"""Gera snippets da gravação CLI a partir dos rótulos inspecionados na interface."""
from pathlib import Path
out=Path(__file__).resolve().parents[2]/'output/playwright/tutorial-xml'
acoes={
'03': """const card=page.locator('li[data-item-xml]').nth(0); await card.scrollIntoViewIfNeeded(); await card.evaluate(el=>el.style.outline='3px solid #38bdf8');""",
'04': """const card=page.locator('li[data-item-xml]').nth(0); await card.getByRole('radio',{name:/Em unidades soltas:/}).check(); await card.getByLabel('Entra no estoque do item 1',{exact:true}).evaluate(el=>el.style.color='#34d399');""",
'05': """await page.locator('li[data-item-xml]').nth(0).evaluate(el=>el.style.outline=''); const card=page.locator('li[data-item-xml]').nth(1); await card.scrollIntoViewIfNeeded(); await card.getByRole('radio',{name:/Em .* fechada:/}).check(); await card.getByLabel('Unidades por embalagem do item 2',{exact:true}).fill('20'); await card.getByLabel('Entra no estoque do item 2',{exact:true}).scrollIntoViewIfNeeded();""",
'06': """const card=page.locator('li[data-item-xml]').nth(1); await card.getByRole('radio',{name:'Só por unidade',exact:true}).check(); await card.getByLabel('Preço de venda do item 2',{exact:true}).fill('2,00'); await card.getByLabel('Preço de venda do item 2',{exact:true}).blur();""",
'07': """const card=page.locator('li[data-item-xml]').nth(2); await card.getByRole('radio',{name:'Caixa fechada e unidade',exact:true}).check(); await card.getByLabel('Entra no estoque do item 3',{exact:true}).scrollIntoViewIfNeeded();""",
'08': """await page.getByLabel('Preço da embalagem do item 3',{exact:true}).fill('48,00'); await page.getByLabel('Preço da unidade do item 3',{exact:true}).fill('4,50'); await page.getByLabel('Preço da unidade do item 3',{exact:true}).blur();""",
'09': """const cb=page.getByRole('checkbox',{name:'Incluir CARTEIRA Palheiro tradicional',exact:true}); await cb.uncheck(); await page.waitForTimeout(650); await cb.check(); await page.getByRole('button',{name:'Confirmar importação',exact:true}).hover();""",
'10': """await page.getByRole('button',{name:'Confirmar importação',exact:true}).click(); await page.getByText('Importado! 1 atualizado(s), 2 novo(s).',{exact:true}).waitFor();""",
'11': """await page.getByRole('row').filter({hasText:'Bebida láctea 200 ml'}).evaluate(el=>el.style.outline='3px solid #34d399');""",
'12': """await page.getByRole('link',{name:'PDV / Vender',exact:true}).click(); await page.getByText('CX com 12',{exact:true}).waitFor();""",
'13': """await page.getByRole('link',{name:'Produtos',exact:true}).click(); const row=page.getByRole('row').filter({hasText:'CARTEIRA Palheiro tradicional'}); await row.getByRole('button',{name:'Editar',exact:true}).click(); await page.waitForTimeout(900); await page.getByText('Preço Venda',{exact:true}).locator('..').locator('input').fill('2,20'); await page.waitForTimeout(1400); await page.getByRole('button',{name:'Salvar Alterações',exact:true}).click(); await page.getByText('Produto atualizado!',{exact:true}).waitFor();""",
'14': """await page.getByRole('link',{name:'Manual',exact:true}).hover();""",
}
for n,js in acoes.items():
    (out/f'{n}.js').write_text('async (page) => { '+js+' await page.waitForTimeout(1300); }',encoding='utf8')
print('Snippets de gravação preparados.')
