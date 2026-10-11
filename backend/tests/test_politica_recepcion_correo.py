from app.services.politica_recepcion_correo import (
    AutorizacionCorreo,
    DecisionCorreo,
    decidir_recepcion,
    puede_administrar_buzon,
    puede_habilitar_empresa,
    puede_registrar_remitente,
)


def caso(registrado=True, gestores=frozenset({"g1"}), receptor="20123456789"):
    return AutorizacionCorreo(
        remitente_autorizado=registrado,
        gestor_ids_validos=gestores,
        ruc_receptor=receptor,
        receptores_autorizados=frozenset({"20123456789"}),
    )


def test_rechaza_no_registrado():
    assert decidir_recepcion(caso(registrado=False)) == DecisionCorreo.RECHAZAR_REMITENTE


def test_gestor_ambiguo_o_ausente():
    assert (
        decidir_recepcion(caso(gestores=frozenset({"g1", "g2"}))) == DecisionCorreo.PENDIENTE_GESTOR
    )
    assert decidir_recepcion(caso(gestores=frozenset())) == DecisionCorreo.PENDIENTE_GESTOR


def test_receptor_ajeno():
    assert decidir_recepcion(caso(receptor="20999999999")) == DecisionCorreo.PENDIENTE_RECEPTOR


def test_receptor_autorizado():
    assert decidir_recepcion(caso()) == DecisionCorreo.ACEPTAR_PARA_INGESTA


def test_roles():
    assert puede_administrar_buzon("ADMINISTRADOR")
    assert not puede_administrar_buzon("RESPONSABLE")
    assert not puede_administrar_buzon("GESTOR")
    assert puede_registrar_remitente("ADMINISTRADOR")
    assert not puede_registrar_remitente("GESTOR")
    assert not puede_registrar_remitente("USUARIO")
    assert puede_habilitar_empresa("GERENTE")
    assert not puede_habilitar_empresa("GESTOR")
