# elasticsearch

이 폴더는 ELK 스택의 Elasticsearch 데이터를 저장하는 용도로 사용됩니다.

- 데이터 볼륨 경로: `./data` (docker-compose.elk.yml에서 마운트)
- 컨테이너 내 경로: `/usr/share/elasticsearch/data`

이 폴더는 Elasticsearch의 영구 데이터를 보관하므로 삭제 시 주의하세요.

> 이 프로젝트에서는 Nginx access.log를 수집하여 Elasticsearch에 저장합니다.