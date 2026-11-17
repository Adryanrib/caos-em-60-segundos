# Caos 60 — teste de mídia real (experimental)

Teste isolado. Lê a fila `clip_queue` do Supabase e seleciona um clipe Twitch de fonte `rights_verified=true`. Usa Streamlink com a URL pública para tentar obter o vídeo, e FFmpeg para renderizar em 1080x1920, até 60s. Salva MP4 em artifact privado à execução (retenção de 1 dia).

- Não cria nem modifica registros no Supabase.
- Não publica vídeos nas redes.
- Não usa cookies, credenciais pessoais da Twitch ou endpoints privados diretamente.
- Se o Streamlink falhar, o job fica vermelho. Isto não significa que o sistema existente deixou de funcionar.
- Esta abordagem depende da disponibilidade de reprodução pública e pode não funcionar com todos os clipes; é experimental e deve seguir as permissões e regras aplicáveis da plataforma.

## Aplicar

Depois de extrair os arquivos na raiz do repositório local:

```bash
git add .github/workflows/media-test.yml scripts/media_test.py tests/test_media_test.py README-PROXIMA-ETAPA.md
git commit -m "feat: teste experimental de clipe Twitch na nuvem"
git push origin main
```

GitHub → Actions → **Caos 60 - teste de clipe real** → Run workflow. Se o job ficar verde, baixe `caos60-primeiro-short-real` na seção Artifacts.

**Observação:** manter o repositório público não dá acesso público ao artifact da execução sem autenticação, mas proteja os vídeos conforme as autorizações recebidas. Nunca compartilhe secrets.
