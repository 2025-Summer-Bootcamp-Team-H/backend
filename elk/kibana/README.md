# kibana

이 폴더는 ELK 스택의 Kibana 설정을 위한 공간입니다.

- 별도의 설정 파일은 필요하지 않으며, docker-compose.elk.yml에서 컨테이너가 자동으로 실행됩니다.
- 브라우저에서 http://localhost:5601 또는 서버IP:5601로 접속해 Nginx 로그를 시각화할 수 있습니다.
- 인덱스 패턴: `nginx-logs-*`로 생성하면 Nginx access.log를 확인할 수 있습니다.