"""Serviços fiscais solicitados explicitamente na tela de suporte fiscal."""
from typing import Literal
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field, model_validator
from datetime import datetime, timezone
from database import db
from fiscal_router import _user
import fiscal_direto

router = APIRouter()


class InutilizacaoInput(BaseModel):
    modelo: Literal['55', '65'] = '65'
    ano: int = Field(ge=2000, le=2099)
    serie: int = Field(ge=0, le=999)
    inicio: int = Field(ge=1, le=999999999)
    fim: int = Field(ge=1, le=999999999)
    justificativa: str = Field(min_length=15, max_length=255)

    @model_validator(mode='after')
    def validar(self):
        if self.inicio > self.fim or self.ano > datetime.now().year:
            raise ValueError('Ano ou intervalo inválido.')
        if len(self.justificativa.strip()) < 15:
            raise ValueError('Justificativa deve ter ao menos 15 caracteres.')
        return self


def _resumo(registro: dict) -> dict:
    return {k: v for k, v in registro.items() if k not in {'xml_pedido', 'xml_retorno'}}


@router.get('/inutilizacoes')
def historico_inutilizacoes(request: Request) -> dict:
    return {'inutilizacoes': [_resumo(r) for r in db.listar_inutilizacoes(_user(request))]}


@router.post('/inutilizacoes')
def inutilizar(request: Request, data: InutilizacaoInput) -> dict:
    user = _user(request)
    config = db.get_config_fiscal()
    if (config.get('provedor_fiscal') or 'sefaz_mt_direto') != 'sefaz_mt_direto':
        raise HTTPException(status_code=400, detail='Inutilização exige emissor SEFAZ-MT direto.')
    if not fiscal_direto.validar_cnpj(config.get('cnpj')):
        raise HTTPException(status_code=400, detail='Configure o CNPJ do emitente antes de inutilizar.')
    pedido = {**data.model_dump(), 'ambiente': config.get('ambiente') or 'homologacao'}
    agora = datetime.now(timezone.utc).isoformat()
    try:
        registro, criado = db.reservar_inutilizacao(
            user, fiscal_direto.so_digitos(config['cnpj']), pedido, agora)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    if not criado:
        return {'inutilizacao': _resumo(registro)}
    try:
        resultado = fiscal_direto.inutilizar_numeracao(config, data.modelo, data.ano, data.serie,
                                                     data.inicio, data.fim, data.justificativa)
    except fiscal_direto.FiscalDiretoError:
        resultado = {'status': 'rejeitada', 'mensagem': 'Pedido não transmitido. Confira os dados e o A1 da loja.'}
    except OSError:
        resultado = {'status': 'processando', 'mensagem': 'Transmissão sem confirmação. Confira a faixa na SEFAZ antes de reutilizar.'}
    registro = db.concluir_inutilizacao(registro['id'], resultado, datetime.now(timezone.utc).isoformat())
    return {'inutilizacao': _resumo(registro)}


@router.get('/status')
def status(request: Request, modelo: Literal['55', '65'] = '65') -> dict:
    _user(request)
    try:
        return fiscal_direto.status_servico(modelo, db.get_config_fiscal())
    except fiscal_direto.FiscalDiretoError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
