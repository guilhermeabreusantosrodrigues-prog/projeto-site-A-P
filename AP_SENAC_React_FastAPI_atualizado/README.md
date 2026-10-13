# Achados & Perdidos SENAC — versão atualizada

Protótipo acadêmico com **duas experiências separadas**: portal público para alunos/funcionários e área administrativa para a equipe de apoio.

## O que já funciona

- Front-end React + Vite com páginas públicas e painel interno distintos.
- Back-end FastAPI com validação de dados.
- Banco SQLite persistente em `backend/achados_perdidos.db` (não perde os cadastros quando o servidor reinicia).
- Cadastro público de objetos perdidos e geração de protocolo.
- Consulta de andamento com protocolo + e-mail cadastrado.
- Lista pública limitada de objetos guardados; não exibe a descrição interna nem o local de armazenamento.
- Login para equipe de apoio e rotas administrativas protegidas por token.
- Cadastro de objetos encontrados e geração automática de sugestões de matching.
- Revisão humana das sugestões, rejeição/aprovação e histórico administrativo.
- Registro de devolução.
- Envio de e-mail após aprovação de correspondência, quando SMTP estiver configurado.
- Mensagens de erro/sucesso no front-end; o botão não fica indefinidamente em “Enviando...” quando a API responde com erro.

## Requisitos

- Python 3.10 ou superior.
- Node.js LTS instalado.
- VS Code (opcional, recomendado).

## 1. Iniciar o back-end (terminal 1)

No VS Code, abra a pasta raiz do projeto e abra um terminal. Execute:

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m uvicorn main:app --reload
```

Se o ambiente `.venv` já existir, não precisa criá-lo novamente. O servidor fica em `http://127.0.0.1:8000` e a documentação da API em `http://127.0.0.1:8000/docs`. **Mantenha esse terminal aberto.**

## 2. Iniciar o front-end (terminal 2)

Abra um segundo terminal no VS Code:

```powershell
cd frontend
npm install
npm run dev
```

Abra o endereço que o Vite mostrar, normalmente `http://localhost:5173`.

## Acesso à área de apoio — somente demonstração local

- Endereço: `http://localhost:5173/apoio/login`
- E-mail: `apoio@senac.com.br`
- Senha: `Apoio@12345`

O primeiro início da API cria esse usuário de demonstração se ele ainda não existir. Para trocar as credenciais em uma instalação nova, defina `AP_ADMIN_EMAIL` e `AP_ADMIN_PASSWORD` no ambiente **antes do primeiro início**. O usuário demo não deve ser usado em produção.

## E-mail de notificação (opcional)

Sem configuração SMTP, o sistema registra a aprovação e informa que o e-mail não foi enviado. Para habilitar e-mail, configure no ambiente do back-end:

- `AP_SMTP_HOST`
- `AP_SMTP_PORT` (padrão `587`)
- `AP_SMTP_USER`
- `AP_SMTP_PASSWORD`
- `AP_SMTP_FROM`

Não coloque senhas SMTP no código nem envie credenciais em repositórios. Use variáveis de ambiente e uma conta de e-mail autorizada.

## Banco de dados

O SQLite é criado automaticamente no primeiro início da API. O arquivo fica em `backend/achados_perdidos.db`. Faça backup desse arquivo antes de removê-lo. Para reiniciar os dados de demonstração, pare o servidor e apague o arquivo de banco conscientemente; isso apaga todos os registros.

## Como testar o fluxo completo

1. No portal público, registre um objeto perdido e guarde o protocolo exibido.
2. Acesse `/apoio/login` e entre com as credenciais locais de demonstração.
3. Em **Cadastrar encontrado**, registre um item com categoria, marca, modelo e cor semelhantes.
4. Abra **Correspondências** e revise a sugestão. O percentual é um score por regras, não uma IA generativa nem uma confirmação de propriedade.
5. Ao aprovar, o sistema atualiza o status da ocorrência e tenta enviar e-mail se SMTP estiver configurado.
6. Em **Devoluções**, selecione o objeto e registre quem retirou. Confirme a propriedade antes de entregar fisicamente.
7. Volte ao portal público e consulte o protocolo usando o e-mail original.

## Limitações importantes do protótipo

- O matching é baseado em regras explicáveis; não usa modelo de IA semântica.
- Não há upload de fotos implementado ainda.
- Sessões administrativas ficam em memória e são encerradas ao reiniciar a API.
- O acesso demo serve apenas para apresentação local. Antes de uso real, implementar gestão de contas e troca de senha, controles de tentativa de login, HTTPS, política de retenção, backups, revisão de segurança e conformidade com a LGPD.
- A aprovação do matching é apenas uma etapa de triagem; a equipe deve validar a propriedade antes da devolução.
