# 원 전극 EIS·CV·참고문헌 보존

원 저장소 PR3 commit `8c3a30a778cc9bf19ccb52ca523598bff0a84650`에서 선택한 파일을 byte/Git blob으로 대조했다.
세부 원 경로·크기·SHA256은 `MIGRATION_MANIFEST.json`에 있다. 원본, 추출/피팅 자료, 조건 기록, 논문을 구분한다.

## EIS 원본과 기준

- `NGG electrode EIS result/1015~1022/`의 **17개 XLSX 원본**을 포함한다. 파일명은 [PBS swelling 시간] [PEDOT:PSS 두께]다.
- 현재 초기 비교의 원본은 `0 0.xlsx`, `0 10.xlsx`, `0 30.xlsx`, `0 50.xlsx`, `0 100.xlsx`다. 1d/2d·`2e` 표기 파일도 원본 그대로 보존하되 동일 프로토콜로 자동 합치지 않는다.
- 초기 측정 근거: PBS1×:DI=8:72 부피비, 명목0.1×PBS, 3전극·노출면적1cm². 원측정 −Z″/−Phase 부호와 변환 규약을 보존한다. 반복 측정/온도/AC진폭/DCbias 등 미확인 항목을 채우지 않는다.
- `tis-java/electrode-data/bare-ngg-eis.json`, `bare-ngg-initial-fit.json`, properties와 원 탐색 `inputs/eis-profiles.json`은 **처리/피팅 자료**다. XLSX 원본이나 dry-contact 실측을 대신하지 않는다.
- Rs는 유효 직렬항이다. 측정 복소Z의 log-frequency Re/Im 보간→Rs 한 번 차감→1cm² 면적 한 번 변환을 보존한다. fitted Q/n 전체 곡선을 경계로 강제하거나 Rs/면적을 두 번 적용하지 않는다.
- 50nm의 원 비수동 subtraction·constrained fallback·Rs/n bound와 창별 불확실성을 보존한다. 기존 fit/PDE는 이번 패키지에서 재실행하지 않았다.

원 초기 EIS 보고서가 인용한 방법 reference는 [Gamry EIS basics](https://www.gamry.com/application-notes/EIS/basics-of-electrochemical-impedance-spectroscopy/)다.
이 링크는 기존 인용의 출처 보존이며 새 dry NGG 계면 검증이나 해당 페이지 전체의 이관을 뜻하지 않는다.

## CV 원본·조건·가공 자료

원본 `tis-java/electrode-data/cv-source/pedot cic.pzfx`는 **461,883 bytes**, 실제형식 **PCFFGRA4 바이너리**다.
SHA256: `d1c6c74591a810dbb569f663bfc67e5b13256f13d4a50f826c96d8934614c369`.
확장자가 pzfx여도 XML로 단정하지 않는다. 원 탐색 inputs의 같은 이름 사본도 해시 동등성을 보존한다.

`cv-paired-50nm.csv`, `cv-paired-100nm.csv`, `cv-profile.json`은 원 binary의 추출/처리 자료다.
각 paired CSV 유효행은1476이며 각 표의 bare 곡선은 서로 다르다. 같은 시편 반복 데이터라고 합치지 않는다.
원 binary record flags·추출 규약과 후속 독립 감사의 범위를 `docs/CV_MEASUREMENT_SETTINGS.md`와
`tis-java/electrode-data/cv-measurement-settings.json`에 보존한다. 이 패키지 작업에서 새 CV 수치 분석을 하지 않았다.

사용자가 확인한 공통 **명목 scan rate는0.1V/s=100mV/s**, 전압V·전류A·면적1cm²다.
설정사진은명목±1V/1640점인데 기록은약−0.80078~+1.000977V/1476점이다. 이 불일치와 시간벡터 부재를 보존한다.
기존 profile의 `scan_rate_V_s:null`은 당시 기록이며 새 확인 문서와 구분한다. 원 profile을 덮어쓰지 않는다.
사진 원본 파일/hash와 원 취득 timestamp/instrument method는 저장소에 없어 **미이관**이다. Ag/AgCl·Pt 정보는 잠정이다.
CV 면적, 명목 scan rate, 설정의 전압 범위를 CSC/CIC·검증된 안전창/사람 자극 한계로 바꾸지 않는다.

## 원 제공 참고 PDF — 본문 공개 제외

원 사용자가 제공한 두 PDF는 로컬 전체 패키지에 보존했다. 첫 두 페이지에 **Elsevier All rights reserved**가 표시돼 있으며
별도 공개 재배포 권한은 확인하지 못했다. 공개 저장소/배포 archive에는 PDF 본문을 포함하지 않는다.

| 원 문헌 | DOI/공식 원문 경로 | 원본 크기·SHA256 |
|---|---|---|
| Goyal, Borkholder, Day. A biomimetic skin phantom for characterizing wearable electrodes in the low-frequency regime. Sensors and Actuators A340(2022),113513 | https://doi.org/10.1016/j.sna.2022.113513 | 4,527,112B; `6d6bd13017e1674f041dccac19ec5f37bee34b50b791c11caa9b8cf09936eaf8` |
| Anand, Lowe, Al-Jumaily. Tissue phantoms to mimic the dielectric properties of human forearm section for multi-frequency bioimpedance analysis at low frequencies. Materials Science & Engineering C96(2019),496–508 | https://doi.org/10.1016/j.msec.2018.11.080 | 3,114,546B; `dd042f66b74a5d42cf335238e6801409364fa20704520293e2971b1fe10cbe60` |

팬텀/전극/복소 물성 reference이며 현재 dry NGG 계면이나3kHz TIS의 직접 실측 검증을 대신하지 않는다.
새 계수 추출·전문 수치 검증은 수행하지 않았다. 원 source 코드/사용자 측정자료/논문/계측 vendor 포맷의 권리를 구분하며
포괄적인 새 MIT/CC 라이선스를 붙이지 않는다. 사용자 소유 EIS·CV 원자료의 공개는 별도로 승인되었다.
원본 XLSX의 creator/외부 링크 metadata와 CV binary의 자격증명/개인경로 문자열 점검에서 관련 항목은 검출되지 않았다.
개인 채팅 보관본·자격증명·작업2 전용 모델/환경은 포함하지 않았다. 원 보고서의 과거 작업2 언급은 이력이며 실행 범위가 아니다.
