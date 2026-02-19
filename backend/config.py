"""애플리케이션 설정 관리."""
import os
from typing import Optional

from dotenv import load_dotenv

# 프로젝트 루트의 .env 파일을 로드한다.
load_dotenv()


class Settings:
    """애플리케이션 설정."""

    # 데이터베이스 설정 (동기 psycopg용)
    # Neon DB URL을 .env 파일에서 가져옴 (기본값 없음 - 필수)
    DATABASE_URL: str

    # LangChain PGEngine / asyncpg용 연결 문자열
    PGENGINE_URL: str

    # OpenAI 설정
    OPENAI_API_KEY: Optional[str]
    OPENAI_MODEL: str

    # 벡터 임베딩 설정
    EMBED_DIM: int

    # API 설정
    API_TITLE: str
    API_VERSION: str
    API_DESCRIPTION: str

    # CORS 설정
    CORS_ORIGINS: list[str]

    # 서버 설정
    HOST: str
    PORT: int

    # 개발/디버그 설정
    DEBUG: bool

    # LLM 모델 설정
    MODEL_BASE_PATH: str
    DEFAULT_MODEL_TYPE: str
    DEFAULT_MODEL_NAME: str

    def __init__(self):
        """설정 초기화 및 검증."""
        # 데이터베이스 설정 (Neon DB URL 필수)
        self.DATABASE_URL = os.getenv("DATABASE_URL") or ""
        if not self.DATABASE_URL:
            raise ValueError(
                "DATABASE_URL 환경 변수가 설정되지 않았습니다. "
                ".env 파일에 Neon DB URL을 설정해주세요. "
                "예: DATABASE_URL=postgresql+psycopg://USER:PASSWORD@HOST.neon.tech/DBNAME?sslmode=require"
            )

        # LangChain PGEngine / asyncpg용 연결 문자열
        # Neon DB URL을 기반으로 asyncpg 형식으로 자동 변환
        pg_url = self.DATABASE_URL.replace("postgresql+psycopg://", "postgresql+asyncpg://")
        self.PGENGINE_URL = os.getenv("PGENGINE_URL", pg_url)

        # OpenAI 설정
        self.OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
        self.OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

        # 벡터 임베딩 설정
        self.EMBED_DIM = int(os.getenv("EMBED_DIM", "1024"))

        # API 설정
        self.API_TITLE = "LangChain RAG API"
        self.API_VERSION = "0.1.0"
        self.API_DESCRIPTION = "LangChain과 pgvector를 사용한 RAG 시스템 API"

        # CORS 설정
        cors_origins_env = os.getenv("CORS_ORIGINS")
        if cors_origins_env:
            # 환경 변수가 있으면 사용
            self.CORS_ORIGINS = cors_origins_env.split(",")
        else:
            # 기본값: 프로덕션 도메인 + 로컬 개발
            self.CORS_ORIGINS = [
                "https://leejinhyung.shop",
                "https://www.leejinhyung.shop",
                "http://localhost:3000",
                "http://localhost:3001",
                "http://localhost:3002",
            ]

        # 서버 설정
        self.HOST = os.getenv("HOST", "0.0.0.0")
        self.PORT = int(os.getenv("PORT", "8000"))

        # 개발/디버그 설정
        # SQLAlchemy engine echo 등에 사용
        self.DEBUG = os.getenv("DEBUG", "false").lower() in ("true", "1", "yes")

        # LLM 모델 설정
        self.MODEL_BASE_PATH = os.getenv("MODEL_BASE_PATH", "./artifacts")
        self.DEFAULT_MODEL_TYPE = os.getenv("DEFAULT_MODEL_TYPE", "exaone")
        self.DEFAULT_MODEL_NAME = os.getenv("DEFAULT_MODEL_NAME", "artifacts/base-models/exaone")

        # 모델 경로 설정 (artifacts 기준)
        self.EXAONE_BASE_MODEL_PATH = os.getenv(
            "EXAONE_BASE_MODEL_PATH", "./artifacts/base-models/exaone"
        )
        self.EXAONE_LORA_PATH = os.getenv(
            "EXAONE_LORA_PATH", "./artifacts/lora-adapters/exaone"
        )
        self.KOELECTRA_SPAM_LORA_PATH = os.getenv(
            "KOELECTRA_SPAM_LORA_PATH", "./artifacts/lora-adapters/koelectra-spam"
        )
        self.KOELECTRA_CALLCENTER_LORA_PATH = os.getenv(
            "KOELECTRA_CALLCENTER_LORA_PATH", "./artifacts/lora-adapters/koelectra-callcenter"
        )
        self.KOELECTRA_GATEWAY_LORA_PATH = os.getenv(
            "KOELECTRA_GATEWAY_LORA_PATH", "./artifacts/lora-adapters/koelectra-gateway/run_20260122_175255"
        )
        self.KOELECTRA_INTENT_LORA_PATH = os.getenv(
            "KOELECTRA_INTENT_LORA_PATH", None
        )
        self.KOELECTRA_BASE_MODEL = os.getenv(
            "KOELECTRA_BASE_MODEL", "monologg/koelectra-small-v3-discriminator"
        )
        self.MIDM_MODEL_PATH = os.getenv(
            "MIDM_MODEL_PATH", "./artifacts/base-models/midm"
        )

        # 의도 기반 라우팅 사용 여부 (기본값: True, exam_flow_v2가 기본이므로)
        self.USE_INTENT_BASED_ROUTING = os.getenv(
            "USE_INTENT_BASED_ROUTING", "true"
        ).lower() in ("true", "1", "yes")

        # 모델 기반 의도 분류 사용 여부 (기본값: False, 모델이 학습되면 True로 변경)
        self.USE_MODEL_BASED_INTENT = os.getenv(
            "USE_MODEL_BASED_INTENT", "false"
        ).lower() in ("true", "1", "yes")

        # TTS / Audio 설정
        self.AUDIO_STORAGE_PATH = os.getenv(
            "AUDIO_STORAGE_PATH",
            os.path.join(os.path.dirname(__file__), "..", "data", "audio")
        )

        # Upstash Redis 설정
        self.UPSTASH_REDIS_REST_URL = os.getenv("UPSTASH_REDIS_REST_URL", "")
        self.UPSTASH_REDIS_REST_TOKEN = os.getenv("UPSTASH_REDIS_REST_TOKEN", "")

        # JWT 설정
        self.JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "your-secret-key-change-in-production")
        self.JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
        self.JWT_ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "30"))

        # 소셜 로그인 설정
        self.KAKAO_REST_API_KEY = os.getenv("KAKAO_REST_API_KEY", "")
        self.KAKAO_CLIENT_SECRET = os.getenv("KAKAO_CLIENT_SECRET", "")
        self.KAKAO_REDIRECT_URI = os.getenv("KAKAO_REDIRECT_URI", "")

        self.NAVER_CLIENT_ID = os.getenv("NAVER_CLIENT_ID", "")
        self.NAVER_CLIENT_SECRET = os.getenv("NAVER_CLIENT_SECRET", "")
        self.NAVER_REDIRECT_URI = os.getenv("NAVER_REDIRECT_URI", "")

        self.GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "")
        self.GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET", "")
        self.GOOGLE_REDIRECT_URI = os.getenv("GOOGLE_REDIRECT_URI", "")

        # 프론트엔드 콜백 URL
        self.FRONT_LOGIN_CALLBACK_URL = os.getenv("FRONT_LOGIN_CALLBACK_URL", "http://localhost:3000")

        # 쿠키 설정
        self.COOKIE_SECURE = os.getenv("COOKIE_SECURE", "false").lower() == "true"
        self.COOKIE_SAME_SITE = os.getenv("COOKIE_SAME_SITE", "lax")


settings = Settings()
