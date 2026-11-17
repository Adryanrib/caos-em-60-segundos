# Caos em 60 Segundos

Automação **pessoal**, na nuvem, começando pela descoberta de clipes da Twitch. Sem dependência de computador ligado.

## O que funciona nesta primeira etapa

- GitHub Actions agenda a consulta da Twitch de 30 em 30 minutos (agendamentos podem atrasar).
- `scripts/discover.py` consulta a API **oficial** Twitch Helix, buscando metadados de clipes publicados nas últimas 24 horas.
- `sources.json` permite adicionar ou pausar vários canais.
- Resultado `output/discovered.json` pode ser baixado nos **Artifacts** de uma execução do workflow.
- Workflow `Caos 60 - teste FFmpeg` gera um vídeo de teste sintético na nuvem, com download em Artifacts.
- `scripts/render.py` transforma um **arquivo local autorizado** em vídeo vertical 9:16, quando integrado a um fluxo de mídia.
- SQL inicial em `supabase/schema.sql`, com RLS ativado e nenhuma política pública.

## Ativar descoberta da Twitch

1. Crie uma aplicação no [Twitch Developer Console](https://dev.twitch.tv/console/apps), obtenha Client ID e Client Secret.
2. GitHub: Settings → Secrets and variables → Actions → New repository secret.
3. Cadastre `TWITCH_CLIENT_ID` e `TWITCH_CLIENT_SECRET` (não compartilhar valores em chats/logs).
4. Vá a Actions → `Caos 60 - descoberta Twitch` → Run workflow.
5. Baixe o artifact `twitch-clips` e confira o arquivo JSON.

Sem secrets, o workflow executa testes mas **não consulta a Twitch**. Não há upload/postagem automática nesta etapa.

## Adicionar canais

Altere `sources.json`:

```json
{"sources":[{"platform":"twitch","channel":"alanzoka","enabled":true,"rights_verified":false}]}
```

`rights_verified` é apenas controle administrativo. Marque true após confirmar a autorização específica para reutilizar e publicar os trechos.

## Testar FFmpeg sem Twitch

Actions → `Caos 60 - teste FFmpeg` → Run workflow. Resultado: artifact `demo-short-video`, 5 segundos, imagem sintética; não usa conteúdo de terceiros.

## Próximas etapas

1. Persistir clipes no Supabase com deduplicação entre execuções.
2. Obter arquivos da Twitch somente por mecanismos oficiais e permissões apropriadas, ou por upload autorizado.
3. Selecionar momentos e renderizar um Short real com legendas e enquadramento inteligente.
4. Adicionar app Next.js na Vercel para dashboard, com login e APIs server-side.
5. Publicar por OAuth no YouTube; integrar Instagram/TikTok quando suas permissões e políticas permitirem.

**Limites:** a API Twitch Helix fornece metadados de clipes; não oferece download irrestrito de qualquer streamer. GitHub Actions não é processamento gratuito ilimitado. O TikTok pode exigir auditoria e o uso precisa atender às políticas de publicação. Não tratar o pipeline como produtor/postador automático completo ainda.
