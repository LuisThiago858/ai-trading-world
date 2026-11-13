import json
from dataclasses import dataclass
from decimal import Decimal

from django.conf import settings
from openai import APIConnectionError, APITimeoutError, OpenAI, RateLimitError
from pydantic import BaseModel, ValidationError

from .schemas import AlexOutput, AssetTechnicalView, MayaOutput, VictorOutput


class LLMProviderError(RuntimeError):
    def __init__(self, message, *, transient=False, code="LLM_PROVIDER_ERROR"):
        super().__init__(message)
        self.transient = transient
        self.code = code


@dataclass(frozen=True)
class ProviderResult:
    data: BaseModel
    provider: str
    model: str
    input_tokens: int = 0
    output_tokens: int = 0
    estimated_cost_usd: Decimal = Decimal("0")


class BaseLLMProvider:
    name = "base"
    mode = "real"

    def generate(self, *, agent, schema, context):
        raise NotImplementedError


class DeterministicMockProvider(BaseLLMProvider):
    name = "deterministic_mock"
    mode = "mock"
    model = "deterministic-mock-v1"

    def generate(self, *, agent, schema, context):
        builders = {
            "ALEX": self._alex,
            "MAYA": self._maya,
            "VICTOR": self._victor,
        }
        try:
            payload = builders[agent](context)
            data = schema.model_validate(payload)
        except (KeyError, TypeError, ValidationError, ValueError) as exc:
            raise LLMProviderError(
                "O mock produziu uma saída incompatível com o schema.",
                code="INVALID_LLM_OUTPUT",
            ) from exc
        return ProviderResult(data=data, provider=self.name, model=self.model)

    @staticmethod
    def _alex(context):
        assessments = []
        selected_asset = None
        selected_action = "HOLD"
        for asset in context["assets"]:
            indicators = context["indicators"][asset]
            change = Decimal(indicators["change_percent"]) if indicators["change_percent"] else None
            if not indicators["history_sufficient"]:
                trend, action = "INSUFFICIENT_DATA", "HOLD"
                favorable = []
                contrary = ["Histórico insuficiente para médias e volatilidade de 20 períodos."]
            elif change is not None and change > Decimal("0"):
                trend, action = "BULLISH", "BUY"
                favorable = ["Variação do período é positiva e calculada sobre candles persistidos."]
                contrary = ["O sinal técnico não garante continuidade da tendência."]
            elif change is not None and change < Decimal("0"):
                trend, action = "BEARISH", "SELL"
                favorable = ["Variação do período é negativa e calculada sobre candles persistidos."]
                contrary = ["A queda pode se reverter e o histórico permanece limitado."]
            else:
                trend, action = "NEUTRAL", "HOLD"
                favorable = []
                contrary = ["Não há direção mensurável suficiente."]
            assessments.append(
                AssetTechnicalView(
                    asset=asset,
                    trend=trend,
                    indicators=indicators,
                    favorable_arguments=favorable,
                    contrary_arguments=contrary,
                    action=action,
                    justification="Conclusão determinística baseada apenas nos indicadores fornecidos.",
                    invalidation_conditions=["Novo snapshot", "Mudança de direção dos indicadores"],
                ).model_dump(mode="json")
            )
            if selected_action == "HOLD" and action != "HOLD":
                selected_asset, selected_action = asset, action
        return {
            "assessments": assessments,
            "selected_asset": selected_asset,
            "action": selected_action,
            "summary": (
                "Mock determinístico: sinal técnico elegível."
                if selected_asset
                else "Mock determinístico: HOLD por ausência de evidência técnica suficiente."
            ),
        }

    @staticmethod
    def _maya(context):
        alex = context["alex"]
        action, asset = alex["action"], alex["selected_asset"]
        positions = {item["symbol"]: Decimal(item["available_quantity"]) for item in context["positions"]}
        if action == "SELL" and (not asset or positions.get(asset, Decimal("0")) <= 0):
            action, asset = "HOLD", None
        allocation = Decimal("2.5") if action != "HOLD" else Decimal("0")
        return {
            "action": action,
            "asset": asset,
            "allocation_percent": allocation,
            "favorable_arguments": ["Alocação proposta permanece abaixo do limite de 5% por operação."] if asset else [],
            "hold_arguments": ["HOLD preserva capital quando a evidência é insuficiente."] if not asset else [],
            "disagreements": [],
            "reasoning": "Comparação determinística entre sinais, exposição e saldo da carteira.",
        }

    @staticmethod
    def _victor(context):
        risk = context.get("risk") or {"approved": True, "codes": []}
        maya_action = context["maya"]["action"]
        allowed = bool(risk["approved"]) and maya_action != "HOLD"
        codes = list(risk.get("codes") or [])
        return {
            "action": maya_action if allowed else "HOLD",
            "risk_allowed": bool(risk["approved"]),
            "risk_codes": codes,
            "approved_checks": ["Motor determinístico não retornou bloqueios."] if risk["approved"] else [],
            "failed_checks": codes,
            "fragile_hypotheses": ["Indicadores históricos não garantem resultado futuro."],
            "reasoning": "Victor apenas explica a decisão do Risk Engine; não pode substituí-la.",
            "suggested_adjustment": None if allowed else "Manter HOLD e revisar os bloqueios determinísticos.",
        }


class OpenAIProvider(BaseLLMProvider):
    name = "openai"
    mode = "real"

    prompts = {
        "ALEX": "Você é Alex, analista técnico. Use somente os indicadores fornecidos. Não invente preços, candles ou indicadores.",
        "MAYA": "Você é Maya, estrategista de carteira. Questione os sinais e nunca exceda 5% de alocação por operação.",
        "VICTOR": "Você é Victor, gerente de risco. A decisão determinística fornecida é soberana; risco reprovado exige HOLD.",
    }

    def __init__(self):
        if not settings.LLM_API_KEY:
            raise LLMProviderError("OPENAI_API_KEY não configurada.", code="LLM_NOT_CONFIGURED")
        self.client = OpenAI(api_key=settings.LLM_API_KEY, timeout=settings.LLM_TIMEOUT_SECONDS)
        self.model = settings.LLM_MODEL

    def generate(self, *, agent, schema, context):
        try:
            response = self.client.responses.parse(
                model=self.model,
                input=[
                    {"role": "system", "content": self.prompts[agent]},
                    {"role": "user", "content": json.dumps(context, ensure_ascii=False)},
                ],
                text_format=schema,
                max_output_tokens=settings.LLM_MAX_OUTPUT_TOKENS,
            )
        except (APITimeoutError, APIConnectionError, RateLimitError) as exc:
            raise LLMProviderError(
                "Provedor de LLM temporariamente indisponível.", transient=True,
                code="LLM_TEMPORARILY_UNAVAILABLE",
            ) from exc
        except Exception as exc:
            raise LLMProviderError("Falha controlada no provedor de LLM.") from exc
        if response.status != "completed" or response.output_parsed is None:
            raise LLMProviderError("Resposta incompleta, recusada ou sem saída estruturada.", code="INVALID_LLM_OUTPUT")
        usage = response.usage
        return ProviderResult(
            data=response.output_parsed,
            provider=self.name,
            model=response.model,
            input_tokens=getattr(usage, "input_tokens", 0) or 0,
            output_tokens=getattr(usage, "output_tokens", 0) or 0,
        )


def get_provider():
    if settings.LLM_PROVIDER == "mock":
        return DeterministicMockProvider()
    if settings.LLM_PROVIDER == "openai":
        return OpenAIProvider()
    raise LLMProviderError(f"Provedor LLM não suportado: {settings.LLM_PROVIDER}", code="LLM_NOT_CONFIGURED")
