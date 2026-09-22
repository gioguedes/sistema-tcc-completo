from src.db.models import Base, Dispositivo, Leitura, Sensor


def test_metadata_tem_as_tabelas_esperadas():
    nomes = set(Base.metadata.tables.keys())
    esperadas = {
        "usuarios",
        "especies",
        "tanques",
        "dispositivos",
        "tipos_sensor",
        "sensores",
        "leituras",
    }
    assert esperadas <= nomes


def test_leitura_tem_chave_primaria_composta():
    colunas_pk = {c.name for c in Leitura.__table__.primary_key.columns}
    assert colunas_pk == {"id", "ts"}


def test_dispositivo_mac_e_unico():
    assert Dispositivo.__table__.c.mac_address.unique is True


def test_sensor_referencia_dispositivo_tipo_e_tanque():
    tabelas_referenciadas = {fk.column.table.name for fk in Sensor.__table__.foreign_keys}
    assert tabelas_referenciadas == {"dispositivos", "tipos_sensor", "tanques"}
