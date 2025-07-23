# logstash

이 폴더는 ELK 스택의 Logstash 설정을 위한 공간입니다.

- `pipeline/logstash.conf`: Nginx access.log를 수집해 파싱/가공 후 Elasticsearch에 저장하는 파이프라인 설정 파일입니다.
- 로그 파일 경로는 docker-compose.elk.yml에서 elk/nginx/log:/var/log/nginx로 마운트됩니다.