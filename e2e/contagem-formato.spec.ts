import { test, expect } from '@playwright/test';
const api = process.env.VF_EMBALAGEM_API || 'http://127.0.0.1:3121';
let token: string;
const headers = () => ({Authorization: `Bearer ${token}`});
const gtinBase = '789000000024';
const gtin = gtinBase + (10 - [...gtinBase].reduce((s,n,i)=>s+Number(n)*(i%2?3:1),0)%10)%10;
test.beforeAll(async ({request}) => {
  const data = {usuario: 'e2e-carrinho', nome: 'Teste descartável', senha: 'fixture-e2e-carrinho'};
  let r = await request.post(`${api}/api/auth/login`, {data});
  if (r.status() === 401) r = await request.post(`${api}/api/auth/registro`, {data});
  expect(r.status()).toBe(200); token = (await r.json()).token;
});
test.beforeEach(async ({page}) => {
  await page.addInitScript(t => localStorage.setItem('vf_token', t), token);
  await page.goto('/produtos');
});
test.afterAll(async ({request}) => {
  const ps=(await (await request.get(`${api}/api/produtos`,{headers:headers()})).json()).produtos;
  for (const p of ps.filter((p:{nome:string})=>['Bebida láctea 24','CARTEIRA Palheiro 24','Cerveja formatos 24','Caixa fechada 24'].includes(p.nome))) {
    const r=await request.delete(`${api}/api/produtos/${p.id}`,{headers:headers()}); expect(r.ok()).toBeTruthy();
  }
});
const xml = (nome: string, codigo: string, qtd: number, preco: number) => `<NFe><infNFe><ide><mod>55</mod><nNF>24</nNF></ide><emit><xNome>Fornecedor teste</xNome></emit><det><prod><cEAN>${codigo}</cEAN><xProd>${nome}</xProd><uCom>UN</uCom><qCom>${qtd}</qCom><vUnCom>${preco}</vUnCom></prod></det></infNFe></NFe>`;

test('Bebida: caixa física com 54 UN na nota não multiplica; reposição mantém preço', async ({page,request}) => {
  const r = await request.post(`${api}/api/produtos`, {headers:headers(),data:{nome:'Bebida láctea 24',codigo_barras:gtin,estoque:54,preco_custo:1.59,preco_venda:2.07,unidade:'UN',unidade_compra:'CX',quantidade_por_embalagem:27}});
  const id = (await r.json()).produto.id;
  await page.locator('input[type=file]').setInputFiles({name:'bebida.xml',mimeType:'text/xml',buffer:Buffer.from(xml('Bebida láctea 24',gtin,54,1.59))});
  const d = page.getByRole('dialog').filter({hasText:'Confirmar importação'});
  await expect(d.getByLabel('Entra no estoque do item 1',{exact:true})).toHaveText('54 UN');
  await expect(d.getByText(/Esta entrada mantém os preços/)).toBeVisible();
  await d.getByRole('button',{name:'Confirmar importação',exact:true}).click();
  await expect(page.getByText(/Importado!/)).toBeVisible();
  const p = (await (await request.get(`${api}/api/produtos/${id}`,{headers:headers()})).json()).produto;
  expect([p.estoque,p.preco_custo,p.preco_venda]).toEqual([108,1.59,2.07]);
  const ativar=await request.put(`${api}/api/produtos/${id}`,{headers:headers(),data:{vende_por_unidade:true,preco_embalagem:48,preco_unidade:2.07}});
  expect(ativar.ok()).toBeTruthy();
  await page.locator('input[type=file]').setInputFiles({name:'reposicao-caixas.xml',mimeType:'text/xml',buffer:Buffer.from(xml('Bebida láctea 24',gtin,2,27))});
  await d.getByRole('radio',{name:/Em CX fechada:/}).check();
  await expect(d.getByLabel('Unidades por embalagem do item 1',{exact:true})).toHaveText('27');
  await expect(d.getByLabel('Entra no estoque do item 1',{exact:true})).toHaveText('54 UN');
  await page.screenshot({path:'output/playwright/reposicao-caixas-24.png',fullPage:true});
  await d.getByRole('button',{name:'Confirmar importação',exact:true}).click();
  await expect(page.getByText(/Importado!/)).toBeVisible();
  const depois=(await (await request.get(`${api}/api/produtos/${id}`,{headers:headers()})).json()).produto;
  expect([depois.estoque,depois.preco_custo,depois.preco_embalagem,depois.preco_unidade]).toEqual([162,1,48,2.07]);
});

test('Palheiro novo: nota em UN pode contar carteiras mesmo vendendo só avulso', async ({page,request}) => {
  await page.locator('input[type=file]').setInputFiles({name:'palheiro.xml',mimeType:'text/xml',buffer:Buffer.from(xml('CARTEIRA Palheiro 24','SEM GTIN',2,10))});
  const d = page.getByRole('dialog').filter({hasText:'Confirmar importação'});
  await d.getByRole('radio',{name:/Em .* fechada:/}).check();
  await d.getByLabel('Unidades por embalagem do item 1',{exact:true}).fill('20');
  await expect(d.getByLabel('Entra no estoque do item 1',{exact:true})).toHaveText('40 UN');
  await d.getByLabel('Preço de venda do item 1',{exact:true}).fill('2');
  await d.getByRole('button',{name:'Confirmar importação',exact:true}).click();
  await expect(page.getByText(/Importado!/)).toBeVisible();
  const ps = (await (await request.get(`${api}/api/produtos`,{headers:headers()})).json()).produtos;
  const p = ps.find((p:{nome:string})=>p.nome==='CARTEIRA Palheiro 24');
  expect([p.estoque,p.preco_custo,p.preco_venda,p.vende_por_unidade]).toEqual([40,0.5,2,0]);
});

test('Só caixa: nota com conteúdo em UN aceita contagem de caixas conferida', async ({page,request}) => {
  await page.locator('input[type=file]').setInputFiles({name:'fechada.xml',mimeType:'text/xml',buffer:Buffer.from(xml('Caixa fechada 24','SEM GTIN',24,2))});
  const d=page.getByRole('dialog').filter({hasText:'Confirmar importação'});
  const trocar=d.getByRole('button',{name:/Vende em caixa também/});
  if(await trocar.isVisible()) await trocar.click();
  await d.getByRole('radio',{name:'Só a embalagem fechada',exact:true}).check();
  await d.getByLabel('Entra no estoque do item 1',{exact:true}).fill('2');
  await d.getByLabel('Custo por unidade do item 1',{exact:true}).fill('24');
  await d.getByLabel('Preço de venda do item 1',{exact:true}).fill('30');
  await d.getByRole('button',{name:'Confirmar importação',exact:true}).click();
  await expect(page.getByText(/Importado!/)).toBeVisible();
  const ps=(await (await request.get(`${api}/api/produtos`,{headers:headers()})).json()).produtos;
  const p=ps.find((p:{nome:string})=>p.nome==='Caixa fechada 24');
  expect([p.estoque,p.preco_custo,p.preco_venda,p.unidade]).toEqual([2,24,30,'CX']);
});

test('Produto cadastrado: preço, dois formatos, avulso e embalagem com conversão conferida', async ({page,request}) => {
  const r=await request.post(`${api}/api/produtos`,{headers:headers(),data:{nome:'Cerveja formatos 24',codigo_barras:'LATA24',estoque:24,preco_custo:2,preco_venda:4}});
  const id=(await r.json()).produto.id;
  await page.reload();
  const row=page.getByRole('row').filter({hasText:'Cerveja formatos 24'});
  await row.getByRole('button',{name:'Editar',exact:true}).click();
  const field=(label:string)=>page.getByText(label,{exact:true}).locator('..').locator('input');
  await field('Preço Venda').fill('4,50');
  await page.getByRole('button',{name:'Salvar Alterações',exact:true}).click();
  await expect(row).toContainText('4.50');
  await row.getByRole('button',{name:'Editar',exact:true}).click();
  await page.getByRole('radio',{name:'Caixa e unidade',exact:true}).check();
  await expect(page.getByLabel('Código da unidade',{exact:true})).toHaveValue('LATA24');
  await page.getByLabel('Nome da embalagem',{exact:true}).fill('CX');
  await field('Qtd por compra').fill('12');
  await page.getByLabel('Preço da embalagem fechada',{exact:true}).fill('48');
  await expect(page.getByLabel('Preço da unidade',{exact:true})).toHaveValue('4.5');
  await expect(field('Preço Venda')).toHaveCount(0);
  await page.getByRole('button',{name:'Salvar Alterações',exact:true}).click();
  await expect(row).toContainText('CX: R$ 48.00');
  const obter=async()=>(await (await request.get(`${api}/api/produtos/${id}`,{headers:headers()})).json()).produto;
  expect((await obter()).estoque).toBe(24);
  await row.getByRole('button',{name:'Editar',exact:true}).click();
  await page.getByRole('radio',{name:'Somente unidade',exact:true}).check();
  await page.getByRole('button',{name:'Salvar Alterações',exact:true}).click();
  expect([(await obter()).preco_venda,(await obter()).estoque,(await obter()).codigo_barras]).toEqual([4.5,24,'LATA24']);
  // Ativar os dois formatos novamente e depois vender somente a caixa.
  await row.getByRole('button',{name:'Editar',exact:true}).click();
  await page.getByRole('radio',{name:'Caixa e unidade',exact:true}).check();
  await page.getByLabel('Preço da embalagem fechada',{exact:true}).fill('48');
  await page.getByRole('button',{name:'Salvar Alterações',exact:true}).click();
  await expect(page.getByText('Produto atualizado!',{exact:true})).toBeVisible();
  await row.getByRole('button',{name:'Editar',exact:true}).click();
  await page.getByRole('radio',{name:'Somente embalagem fechada',exact:true}).check();
  await page.getByRole('button',{name:'Salvar Alterações',exact:true}).click();
  await expect(page.getByText(/Confira o estoque e o custo na nova unidade/).first()).toBeVisible();
  await page.getByRole('button',{name:'Converter estoque e custo pela embalagem'}).click();
  await page.getByRole('button',{name:'Salvar Alterações',exact:true}).click();
  await expect(page.getByText('Produto atualizado!',{exact:true})).toBeVisible();
  expect([(await obter()).estoque,(await obter()).preco_custo,(await obter()).preco_venda,(await obter()).unidade]).toEqual([2,24,48,'CX']);
  await row.getByRole('button',{name:'Editar',exact:true}).click();
  await page.getByRole('radio',{name:'Caixa e unidade',exact:true}).check();
  await field('Qtd por compra').fill('12');
  await page.getByLabel('Preço da unidade',{exact:true}).fill('4,50');
  await page.getByRole('button',{name:'Converter estoque e custo pela embalagem'}).click();
  await page.getByRole('button',{name:'Salvar Alterações',exact:true}).click();
  await expect(page.getByText('Produto atualizado!',{exact:true})).toBeVisible();
  expect([(await obter()).estoque,(await obter()).preco_custo]).toEqual([24,2]);
  await page.setViewportSize({width:390,height:844});
  await page.locator('article').filter({hasText:'Cerveja formatos 24'}).getByRole('button',{name:'Editar',exact:true}).click();
  await page.screenshot({path:'output/playwright/formato-24-mobile.png',fullPage:true});
});
