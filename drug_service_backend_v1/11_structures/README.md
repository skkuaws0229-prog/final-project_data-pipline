# Structure File Cache

이 폴더는 FastAPI가 `/api/structures/{structure_id}/file` endpoint로 제공할 구조 파일 cache이다.

GitHub에는 대량 구조 파일을 올리지 않고, S3를 기준으로 관리한다.

현재 pilot 파일:

```text
11_structures/alphafold/P23458/AF-P23458-F1-model_v6.cif
```

S3 위치:

```text
s3://say2-4team/20260408_new_pre_project_biso/drug_service_build/11_structures/alphafold/P23458/AF-P23458-F1-model_v6.cif
```

로컬/EC2에서 viewer proxy를 테스트할 때는 S3에서 이 폴더 구조 그대로 내려받은 뒤 Docker Compose를 실행한다.
