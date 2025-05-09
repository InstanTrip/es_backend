# ES Backend
엘라스틱서치 제어함

### 실행법
server/config.py 파일을 만들고
```python
from server.sample_config import Config

class Development(Config):
    ES_HOST = '엘라스틱서치서버 주소'
    ES_PORT = 엘라스틱서치 포트 번호

    WEB_HOST = '0.0.0.0'
    WEB_PORT = 서버 포트 번호
```
적당히 채워넣은 후
```sh
python -m server
```