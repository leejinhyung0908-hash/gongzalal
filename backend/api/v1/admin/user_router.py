"""사용자 라우터.

새 테이블 구조:
- Users: display_name, age, employment_status, base_score, daily_study_time, target_date
"""

from fastapi import APIRouter, HTTPException

from backend.domain.admin.models.transfers.user_transfer import (
    UserCreateRequest,
    UserResponse,
)
from backend.domain.admin.hub.orchestrators.user_flow import UserFlow

router = APIRouter(tags=["users"])

# Orchestrator 인스턴스 (싱글톤 패턴)
_flow = UserFlow()


@router.post("/", response_model=dict)
async def create_user(request: UserCreateRequest) -> dict:
    """사용자 생성/갱신 엔드포인트.

    KoELECTRA로 요청을 분석하여 규칙/정책 기반으로 분기 처리:
    - 규칙 기반: 명확한 경우 → user_service
    - 정책 기반: 애매한 경우 → user_agent

    Args:
        request: 사용자 생성/갱신 요청

    Returns:
        처리 결과
    """
    try:
        # 요청 텍스트 생성 (KoELECTRA 분석용)
        request_text = f"사용자 생성/갱신 요청: display_name={request.display_name}, age={request.age}"

        # Orchestrator로 요청 처리
        result = await _flow.process_user_request(request_text, request.model_dump())

        if not result.get("success", False):
            raise HTTPException(status_code=400, detail=result.get("error", "처리 실패"))

        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as exc:
        print(f"[UserRouter] 오류 발생: {exc}", flush=True)
        import traceback

        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"서버 오류: {str(exc)}")


@router.get("/{user_id}", response_model=dict)
async def get_user(user_id: int) -> dict:
    """사용자 조회 엔드포인트.

    Args:
        user_id: 사용자 ID

    Returns:
        사용자 정보
    """
    try:
        from backend.domain.admin.spokes.services.user_service import UserService

        service = UserService()
        user = await service.get_user_by_id(user_id)

        if not user:
            raise HTTPException(status_code=404, detail="사용자를 찾을 수 없습니다.")

        return {"success": True, "user": user}
    except HTTPException:
        raise
    except Exception as exc:
        print(f"[UserRouter] 오류 발생: {exc}", flush=True)
        import traceback

        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"서버 오류: {str(exc)}")
