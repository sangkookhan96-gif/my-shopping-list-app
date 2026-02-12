# Phase 1: Local Neo4j Graph Model Architecture

---

| 항목 | 값 |
|------|-----|
| **Version** | v1.0 |
| **Status** | FROZEN |
| **Phase** | local_development |
| **Created** | 2026-02-12 |
| **Change Policy** | Pull Request Only |

---

## 1. 설계 목표

- 로컬 Neo4j 기반 데이터 모델 설계 및 검증
- 기사 기반 엔티티 추출 구조 정의
- 향후 Neo4j Aura 이전 가능 구조

### 성공 기준

| 기준 | 목표 |
|------|------|
| 엔티티 추출 정확도 | 80% 이상 |
| 중복률 | 5% 이하 |
| 노드 축적 | 5,000개 이상 |

---

## 2. Graph 파이프라인 실행 조건 (필수)

| 번호 | 조건 |
|------|------|
| 1 | 기사 게시 API 응답 이후에만 실행 |
| 2 | 메인 API와 분리된 Worker 프로세스에서 실행 |
| 3 | 기사 DB 트랜잭션과 Graph 트랜잭션 절대 공유 금지 |
| 4 | 동시 실행 작업 수 = 1 |
| 5 | Graph 실패 시 기사 서비스 영향 없음 |
| 6 | 최대 3회 재시도 후 manual_review 전환 |
| 7 | 모든 처리에 timeout 적용 |
| 8 | GRAPH_SYNC_ENABLED=false 시 즉시 중단 |

---

## 3. 노드 타입 정의

### 3.1 Article
```cypher
(:Article {
    id: String,           // art_{news_id}
    news_id: Integer,
    title_ko: String,
    title_zh: String,
    source: String,
    published_at: DateTime,
    created_at: DateTime
})
```

### 3.2 Institution
```cypher
(:Institution {
    id: String,           // inst_{hash}
    name_ko: String,
    name_zh: String,
    type: String,         // government|regulatory|research
    level: String,        // central|provincial|municipal
    created_at: DateTime
})
```

### 3.3 Policy
```cypher
(:Policy {
    id: String,           // pol_{date}_{seq}
    name_ko: String,
    name_zh: String,
    type: String,         // regulation|guideline|notice
    status: String,       // draft|active|expired
    created_at: DateTime
})
```

### 3.4 Industry
```cypher
(:Industry {
    id: String,           // ind_{code}
    name_ko: String,
    name_zh: String,
    sector: String,
    created_at: DateTime
})
```

### 3.5 Company
```cypher
(:Company {
    id: String,           // comp_{stock_code}
    name_ko: String,
    name_zh: String,
    stock_code: String,
    exchange: String,
    created_at: DateTime
})
```

### 3.6 Indicator
```cypher
(:Indicator {
    id: String,           // kpi_{code}
    name_ko: String,
    name_zh: String,
    category: String,
    unit: String,
    created_at: DateTime
})
```

### 3.7 Region
```cypher
(:Region {
    id: String,           // reg_{code}
    name_ko: String,
    name_zh: String,
    level: String,
    created_at: DateTime
})
```

### 3.8 Event
```cypher
(:Event {
    id: String,           // evt_{date}_{seq}
    name_ko: String,
    name_zh: String,
    type: String,
    event_date: Date,
    created_at: DateTime
})
```

---

## 4. 관계 타입 정의

| 관계 | 설명 | time 속성 |
|------|------|-----------|
| `(:Institution)-[:ANNOUNCED]->(:Policy)` | 기관이 정책 발표 | announced_at |
| `(:Policy)-[:AFFECTS]->(:Industry)` | 정책이 산업에 영향 | - |
| `(:Company)-[:BELONGS_TO]->(:Industry)` | 기업의 산업 분류 | - |
| `(:Article)-[:MENTIONS]->(:Institution)` | 기사가 기관 언급 | - |
| `(:Article)-[:MENTIONS]->(:Company)` | 기사가 기업 언급 | - |
| `(:Article)-[:REPORTS_ON]->(:Policy)` | 기사가 정책 보도 | - |
| `(:Article)-[:COVERS]->(:Industry)` | 기사가 산업 다룸 | - |
| `(:Article)-[:CITES]->(:Indicator)` | 기사가 지표 인용 | value, period |

---

## 5. ID 전략

| 노드 타입 | ID 형식 | 예시 |
|-----------|---------|------|
| Article | `art_{news_id}` | `art_12345` |
| Institution | `inst_{hash}` | `inst_a1b2c3` |
| Policy | `pol_{YYYYMMDD}_{seq}` | `pol_20260212_001` |
| Industry | `ind_{code}` | `ind_semiconductor` |
| Company | `comp_{stock_code}` | `comp_600519` |
| Indicator | `kpi_{code}` | `kpi_gdp` |
| Region | `reg_{code}` | `reg_shanghai` |
| Event | `evt_{date}_{seq}` | `evt_20260212_001` |

---

## 6. 중복 방지 전략

### MERGE 패턴
```cypher
MERGE (i:Institution {name_zh: $name_zh})
ON CREATE SET
    i.id = $id,
    i.name_ko = $name_ko,
    i.created_at = datetime()
ON MATCH SET
    i.updated_at = datetime()
RETURN i
```

### 명칭 표준화
```python
INSTITUTION_ALIASES = {
    "央行": "中国人民银行",
    "证监会": "中国证券监督管理委员会",
    "发改委": "国家发展和改革委员会",
    "工信部": "工业和信息化部",
}
```

---

## 7. 인덱스 전략

```cypher
CREATE INDEX idx_institution_name_zh FOR (n:Institution) ON (n.name_zh);
CREATE INDEX idx_company_name_zh FOR (n:Company) ON (n.name_zh);
CREATE INDEX idx_policy_id FOR (n:Policy) ON (n.id);
CREATE INDEX idx_article_id FOR (n:Article) ON (n.id);
```

---

## 8. 기사 → Graph 변환 흐름

```
기사 게시 완료
    │ [API 응답 반환 후]
    ▼
큐 등록 (graph_sync_queue)
    │ [Worker 프로세스]
    ▼
엔티티 추출 (timeout: 30s)
    ▼
표준화 처리
    ▼
MERGE 적용
    ▼
Neo4j 동기화 (timeout: 60s)
    │
    ├─[성공]→ 완료
    │
    └─[실패]→ 재시도 (최대 3회) → manual_review
```

### 동기화 큐 테이블

```sql
CREATE TABLE graph_sync_queue (
    id INTEGER PRIMARY KEY,
    news_id INTEGER NOT NULL,
    status TEXT DEFAULT 'pending',
    retry_count INTEGER DEFAULT 0,
    error_message TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

---

## 9. Aura 이전 시 수정 요소

| 항목 | 로컬 | Aura |
|------|------|------|
| 연결 URL | `bolt://localhost:7687` | `neo4j+s://xxx.neo4j.io` |
| TLS | 선택 | 필수 |
| 백업 | 수동 | 자동 |

---

## 변경 이력

| 버전 | 일자 | 변경 내용 |
|------|------|----------|
| v1.0 | 2026-02-12 | 최초 작성 및 고정 |

---

**이 문서는 Phase 1 기준 아키텍처로 고정(FROZEN)되었습니다.**
**변경은 Pull Request 방식으로만 허용됩니다.**
