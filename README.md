# CHAMADOS TI — v2.2 (Sollus)
- Login moderno (tema Sollus), LDAP opcional
- Dashboard de chamados
- Anexos com multi-upload (drag-and-drop)
- Relatórios com Chart.js
- Tema claro/escuro
- Painel Admin

## Setup rápido
1) `copy .env.example .env` e ajuste `SECRET_KEY`, `DATABASE_URL`.
2) `python -m venv venv && call venv\Scripts\activate && pip install -r requirements.txt`
3) Migrações: `flask --app app:app db init && flask --app app:app db migrate -m "init" && flask --app app:app db upgrade`
4) Crie um usuário: `flask --app app:app create-user`
5) Rode: `flask --app app:app run -h 0.0.0.0 -p 5920`
