from src.db.models import Especie


def test_db_session_cria_dado(db_session):
    especie = Especie(
        nome_comum="Tilapia",
        nome_cientifico="Oreochromis niloticus",
        ph_min=6.5,
        ph_max=8.5,
        temp_min=20.0,
        temp_max=30.0,
        od_min=4.0,
        od_max=8.0,
    )
    db_session.add(especie)
    db_session.commit()

    assert db_session.query(Especie).count() == 1


def test_db_session_nao_ve_dado_do_teste_anterior(db_session):
    assert db_session.query(Especie).count() == 0