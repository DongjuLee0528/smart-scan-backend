# Plan: scanner-event-trigger

**Status**: Plan  
**Created**: 2026-05-19  
**Feature**: RFID 스캐너 이벤트 기반 트리거

---

## Executive Summary

| 관점 | 내용 |
|------|------|
| **Problem** | 스캐너가 2초마다 루프를 돌며 `/inbound`를 반복 호출 — 태그가 리더기 근처에 있으면 쿨다운마다 이메일 발송 |
| **Solution** | 태그 등장 이벤트 감지 시 1회 전송 후 태그 소멸까지 대기 — 외출·귀가 양방향 자동 처리 |
| **기능 UX** | 현관 통과 시에만 스캔 이벤트 발생 (외출: 누락 감지 / 귀가: 밖에 두고 온 물건 감지) |
| **핵심 가치** | 이메일 알림이 실제 "외출/귀가 이벤트"에만 발송됨 |

---

## Context Anchor

| 항목 | 내용 |
|------|------|
| **WHY** | 연속 스캔으로 인한 중복 이메일 제거, 실생활 외출/귀가 패턴에 맞는 알림 |
| **WHO** | 현관 RFID 리더기 앞을 오가는 가족 구성원 |
| **RISK** | RFID 간헐적 감지 불안정으로 이벤트 오인식 가능성 |
| **SUCCESS** | 외출 1회 → 이메일 최대 1회 / 귀가 1회 → 이메일 최대 1회 |
| **SCOPE** | `raspberry-pi/rfid-scanner/scanner.py` 만 수정 (Lambda·DB 변경 없음) |

---

## 1. 요구사항

### 기능 요구사항

| ID | 요구사항 | 우선순위 |
|----|----------|----------|
| FR-01 | 태그가 새로 감지되면(IDLE → 감지) 스캔 이벤트 시작 | Must |
| FR-02 | 스캔 윈도우(기본 3초) 동안 수집된 태그를 `/inbound` 1회 전송 | Must |
| FR-03 | 전송 후 태그가 완전히 사라질 때까지(Clear 판정) 재전송 금지 | Must |
| FR-04 | 태그 재등장 시(귀가) 새 이벤트로 동일 로직 반복 | Must |
| FR-05 | Clear 판정 임계값(`CLEAR_WAIT_SEC`)을 config.env로 설정 가능 | Should |

### 비기능 요구사항

| ID | 요구사항 |
|----|----------|
| NFR-01 | RFID 간헐적 미감지(flicker) 허용 — Clear 판정 전 짧은 빈틈은 무시 |
| NFR-02 | Lambda·DB 변경 없음 — Edge(Pi) 단독 수정 |
| NFR-03 | Mock 모드에서도 동일하게 동작 |

---

## 2. 현재 구조 vs 목표 구조

### 현재 (연속 폴링)

```
[루프 매 2초]
  collect_tags(3초) → tags 있으면 → POST /inbound → 2초 대기 → 반복
```

문제: 태그가 리더기 근처에 있으면 매 5초마다 `/inbound` 호출

### 목표 (이벤트 기반 상태 머신)

```
IDLE
  ↓ 태그 감지됨
SCANNING (collect_tags window_sec 동안 최대한 수집)
  ↓ 전송 완료
WAITING_CLEAR (태그 소멸 확인 중)
  ↓ CLEAR_WAIT_SEC 동안 태그 없음 확인
IDLE (다음 이벤트 대기)
```

- **IDLE → SCANNING**: 최초 태그 감지 시
- **SCANNING → WAITING_CLEAR**: `/inbound` 전송 직후
- **WAITING_CLEAR → IDLE**: CLEAR_WAIT_SEC 동안 태그 감지 없을 때
- **WAITING_CLEAR → WAITING_CLEAR**: 아직 태그 감지됨 → 계속 대기

---

## 3. 구현 범위

### 변경 파일

| 파일 | 변경 내용 |
|------|-----------|
| `raspberry-pi/rfid-scanner/scanner.py` | 상태 머신 로직 추가 |

### 추가 config.env 파라미터

| 키 | 기본값 | 설명 |
|----|--------|------|
| `CLEAR_WAIT_SEC` | `10` | 태그 소멸 판정 대기 시간 (초) |

### 변경 없는 파일

- `fi805f_reader.py` — 드라이버 그대로 사용
- `api_client.py` — 클라이언트 그대로 사용
- Lambda 코드 — 변경 없음
- Supabase DB — 변경 없음

---

## 4. 상태 전환 상세

```python
# 상태: IDLE
while True:
    tags = reader.collect_tags(window_sec=scan_window)
    
    if not tags:
        time.sleep(SCAN_INTERVAL_SEC)
        continue
    
    # 상태: SCANNING → 즉시 전송
    client.send_scan(tags)
    
    # 상태: WAITING_CLEAR
    logger.info("스캔 이벤트 완료 — 태그 소멸 대기 중...")
    while True:
        time.sleep(2)
        check = reader.collect_tags(window_sec=1.0)
        if not check:
            logger.info("태그 소멸 확인 — 다음 이벤트 대기")
            break
    
    # 상태: IDLE
```

---

## 5. 엣지 케이스

| 케이스 | 처리 방법 |
|--------|-----------|
| RFID flicker (태그 잠깐 사라짐) | `collect_tags(window_sec=1.0)` 재시도로 자연 흡수 |
| 가족 여러 명 동시 외출 | 동일 이벤트에 전체 태그 수집됨 (이미 처리됨) |
| 태그 리더기 위에 영구 방치 | 최초 1회만 전송, WAITING_CLEAR에서 영구 대기 (이메일 반복 없음) |
| Pi 재시작 시 태그 근처 있음 | 부팅 후 최초 감지를 이벤트로 처리 (허용 가능한 동작) |

---

## 6. 성공 기준

- [ ] 태그 5개 올렸다 내렸다 (외출 시뮬레이션) → `/inbound` 정확히 1회 호출
- [ ] 태그 리더기 옆에 방치 → 최초 1회 이후 추가 호출 없음
- [ ] 태그 올렸다가 내리고 다시 올림 (귀가 시뮬레이션) → 총 2회 호출
- [ ] `CLEAR_WAIT_SEC=5` 설정 시 5초 뒤 초기화 확인

---

## 7. 배포 계획

1. `scanner.py` 수정
2. Pi SSH 배포 (`scp` + `docker compose restart rfid-scanner`)
3. 태그 올렸다/내렸다 시나리오 직접 테스트
4. 이상 없으면 git commit → qa push
