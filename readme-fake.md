**Índice**

[[_TOC_]]

---

# Introdução (Overview)

- **WrkSrv_CESOP**
  
- **Equipa Responsável:**
  - Billing Interfaces
  - LDF26 PT Equipa Digital Billing Interfaces
- **Última Actualização:**
  - 17/09/2025

---

# Objetivo do Worker Service

O WrkSrv_CESOP tem como objetivo efetuar a geração do reporte trimestral CESOP. \
Este reporte trata-se de um ficheiro XML.

---

# Principais requisitos

## Contexto de negócio
A Cofidis como PSP (Prestadora de Serviços de Pagamento) ao emitir cartões de crédito e por estarmos presente em Portugal, Estado-Membro da União Europeia, somos obrigados a manter registos dos pagamentos transfronteiriços e a comunicar trimestralmente à Autoridade Tributária dados relativos a estas transações, uma vez que determinados critérios sejam atendidos.  

Por sua vez, as AT’s dos Estados-Membro da União Europeia centralizarão esta informação numa base de dados Europeia designada por "CESOP“(Central Electronic System Of Payment information). \
Essas informações no CESOP serão então disponibilizadas aos especialistas antifraude dos Estados-Membro por meio de uma rede chamada Eurofisc, com o objetivo de dar instrumentos para detetar possíveis fraudes no VAT em transações de e-commerce ocorridos em comércios estabelecidos em outro Estado-Membro ou fora do EEE* (Espaço Econômico Europeu).

## Regras de negócio 
- Pagamentos transfronteiriços realizados com Cartão de Crédito Cofidis (Ordenante) são  elegíveis quando o PSP do Comércio (Beneficiário) não pertencer à EEE, e a obrigação de reporte dessas transações é do PSP do Ordenante, ou seja, da Cofidis Portugal. (Obs.: as transações realizadas nos Estados-Membro do EEE também são elegíveis a serem reportadas, entretanto a responsabilidade do reporte é do PSP do Beneficiário, ou seja, não é a Cofidis Portugal);

- Entretanto, somente devem ser reportadas as transações, onde haja pelo menos 25 transações por Comércio (Beneficiário) num trimestre;

> [!EXEMPLO]
> Se um comércio localizado nos EUA processar mais do que 25 transações provenientes de cartões de crédito emitidos pela Cofidis num trimestre, essas transações devem ser reportadas a CESOP. Agora, se um comércio localizado na Alemanha processar mais do que 25 transações provenientes de cartões de crédito emitidos pela Cofidis num trimestre, estas também serão reportadas, porém pelo PSP que processou essas transações na Alemanha. 

- A periodicidade do envio do reporte é trimestral. 


- O ficheiro é no formato XML e deve seguir o manual TAXUD-2022-00763-00-02-CESOP PT-TRA-00 que contém as orientações funcionais e seguir a especificação técnica CESOP - XSD User Guide-v4.61.


- Não é a Cofidis Portugal que deve transmitir o reporte a CESOP, mas sim a AT Portugal. As regras de transmissão ainda não foram definidas pela AT, entretanto, foi definido que o formato do ficheiro será conforme especificado pela CESOP e que pelo software validador a AT possui conexão com a CESOP.


- Caso não haja transações que não satisfaçam os critérios, mesmo assim o reporte precisa ser gerado e transmitido para à AT e assim à CESOP, conforme regras da especificação técnica. 


---

# Arquitetura

![imagem.png](img/diagrama-arquitetura.png)

## Tech Stack 
  - DotNetCore 8.0
  - C#
  - Entity Framework

---

# Como funciona

O Worker corre de hora a hora, validando o seu agendamento via `ControloExecucao`. \
O agendamento deste `Worker` pode ser consultado via:

```sql
select *
from interfacesdah.dbo.cof_controloexecucao
where idtarefa = 15
order by 1 desc
```

Existe ainda uma outra particularidade relevante.
Por norma, para obter o período de reporte o `Worker` vai obter a `data de billing` atual e posicionar-se no trimestre anterior.\
Contudo, é possível forçar a execução para um determinado trimestre através da tabela `COF_U_CESOP_Controlo`.


![imagem.png](img/diagrama-fluxo.png)

Caso tenha agendamento criado, o `Worker` avança com a sua execução.\
No final do processo de obtenção dos dados, criação do reporte e validação do mesmo (XSD e Módulo Central) o `Worker` deve atualizar o agendamento atual e efetuar o próximo.\
Caso a geração do reporte seja bem sucedida, a próxima execução é agendada para o início do próximo trimestre; em caso de erros, volta a agendar para uma hora depois.


---

# Configuração

---

# Correr no ambiente local / desenvolvimento

- Cumprir requisitos do diagrama de arquiterura
- Adaptar ficheiros de configuração `appSettings.json` e `appSettingsDevelopment.json`.

---

# Instalação / Deployment

A aplicação tem 3 pipelines associadas:


| Pipeline        | Ação               |
|-----------------| -------------------|
| azure-pipelines.yml | Responsável pela geração de um artefacto; corre automaticamente para os branches de quality e master;
| azure-pipelines-ci.yml | Responsável de continua integração de código; corre automaticamente para todos os branches excepto quality e master;
| azure-pipelines-sonarqube.yml | Responsável pela análise de código da aplicação; corre sempre, mas só faz efeito no branch de quality, publicando o resultado da análise de código no sonaqube;

---

# Logging & Monitorização

Logs via ELK via index pattern `logs-wrksrv-cesop`.

---

# Testes

---

# Resolução de problemas / troubleshooting

---

# Glossário

[Link Sharepoint](https://ra.cofidis.pt/sites/dsi/billing/Shared%20Documents/Forms/AllItems.aspx?FolderCTID=0x012000DB2A5DD5AE1CCE47B6560167FBC1C934&id=%2Fsites%2Fdsi%2Fbilling%2FShared%20Documents%2FDocumentos%2F03%20Iniciativas%2FNeg%C3%B3cio%2F446349%20%2D%20Reporte%20CESOP)

---
