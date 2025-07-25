# Filebeat

이 폴더는 Filebeat 설정을 위한 공간입니다.

- `config/filebeat.yml`: Nginx 웹서버 access.log를 수집해 Logstash로 전송하는 설정 파일입니다.
- Filebeat 컨테이너는 `elk/nginx/log` 폴더를 `/var/log/nginx`로 마운트하여 로그를 읽습니다.
- Logstash(5044 포트)로 로그를 전송하며, logstash.conf에서 파싱/가공 후 Elasticsearch에 저장됩니다.
- 이 프로젝트에서는 FastAPI 로그가 아닌 Nginx access.log만 수집합니다.