from app.models.chat_enums import ChatFlowState


def avanzar_estado_flujo_chat(actual: ChatFlowState, mensaje: str) -> ChatFlowState:
    if actual == ChatFlowState.GREETING:
        return ChatFlowState.DISCOVERY
    if actual == ChatFlowState.DISCOVERY and len(mensaje.strip()) > 12:
        return ChatFlowState.SCOPE
    if actual == ChatFlowState.SCOPE:
        return ChatFlowState.ESTIMATE
    if actual == ChatFlowState.ESTIMATE:
        return ChatFlowState.CONTACT
    return actual
