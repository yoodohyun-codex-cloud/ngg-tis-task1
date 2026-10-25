# 작업 1: fine-XY 결과와 원본 전송

이전 worker90469는 2026-10-25 05:16:43 UTC에 정상 완료됐습니다. 실제 프로세스와 세 잠금의 FLOCK/POSIX 상태를 확인한 뒤 단일 계산 소유자가 다음 유한 배치를 수행했습니다. 실행 영수증, 원본 및 실패 증거는 보존했습니다.

새 fine-XY CEM은 동일 물성·회로, 물리적 225 mm² 패드와 fractional contact mask를 사용한 2000 Hz의 2 RHS입니다. 793,848 평가 셀, 21개 계약 검사 통과, 계산 커널 7.91초, 해당 소유자의 RSS+전체 작업 tmpfs 최고 합계 4,776,902,042바이트였습니다. CPU4, 총 8,000,000,000바이트(7.45058 GiB), 80만 평가 셀 제한과 누적 시간 무제한을 유지했습니다. CPU 상한은 실제 4코어 사용률을 뜻하지 않습니다.

계산 완료와 수렴 판정은 별개입니다. 두 basis 모두 사용 가능한 전기적 비교 기준 14개 중 13개를 통과하지 못했습니다. Source0의 접촉 J RMS 최대값은 0.06995376→0.14263729 A/m²(+103.90%), 물리적 가장자리 0.5 mm 띠의 J95는 +42.78%, source 전력은 +2.6926%입니다. whole-contact J95는 −0.00960%로 거의 같았습니다. 높은 국소 최대값을 피부 전체의 균일한 부담으로 해석하지 않습니다.

물리 좌표 교차 면적·깊이 quadrature로 비교했습니다. SC 계면 전류의 primary pairwise L2 절대 차이는 0.00594391337 A/m²(기준 norm 0.0376498438 A/m², 15.78735%)입니다. 평균 투영 후 7.82368%는 별도 보조 지표이며 평균화로 변동을 가립니다. 인덱스 차이나 작은 전위 차이를 E/TIS 수렴으로 판정하지 않았습니다. 기존 실패 플래그와 추정 차수·절대오차를 보존했으며 후보는 미채택입니다. 이 배치는 한 carrier의 해이므로 TIS나 활성화·안전 검증 결과가 아닙니다.

후속 독립 SC-column 제조해 6조건과 6개 검사를 완료했습니다. 부분 접촉의 전체 픽셀 자유도가 국소 최대값 증가를 만들 수 있음을 진단했으며, lateral spread·전체 3D·50 Ω 회로의 검증이나 실제 접촉 보정값으로 사용하지 않습니다. 다음 선정 과제는 접촉 경계를 해상하는 formulation의 제조해/극한 검증입니다. 아직 실행되지 않은 다음 과제를 실행 중으로 표시하지 않습니다. 현재 수치 소유자는 유한 배치 완료 상태이며, 중복 소유자가 없습니다.

[상세 수치와 진단](https://github.com/yoodohyun-codex-cloud/ngg-tis-task1/blob/031a14cf7ad06bf05b3f46786c3d2048decf6b41/docs/TASK1_FINE_XY_TRANSFER_20261025/REPORT.md), [완료 상태](continuation-status.json), [manifest](transfer-manifest.json).

## 전송 범위와 검증

U19, basis audit, coarse/fine DtN·CEM 및 XY benchmark의 원시 배열, 코드, 출처와 영수증을 434개 다운로드 객체로 연결했습니다. 총 1,320,395,491바이트(약 1.320 GB), 별칭 123개, 보존 archive 내부 항목 273개입니다. Q 원본 31개 1,030,059,648바이트도 포함합니다. 요구된 공개 원본·의존성 누락은 0개입니다. 각 파일은 전체 고정 커밋, 저장소 상대 경로, 크기, SHA256과 안전한 상대 저장 경로로 지정되어 있습니다. 내부 절대 경로나 개인 Windows 경로는 manifest에 넣지 않았습니다.

Manifest: 431549바이트, SHA256 `d6fea0b0ad96e49ab434dc559af391085aa8f402bb0cf5d6c228aa57b1b65eb6`.

클라우드에서 공개 파일의 byte/hash readback을 검증했습니다. 이것은 Windows 백업 완료나 과학적 검증을 뜻하지 않습니다. 실제 Windows 저장과 OneDrive 동기화는 모두 미확인입니다. 해시만으로 백업 완료라고 표시하지 않습니다.

## 실제 Windows 수신

[수신기](../../tools/windows_transfer_20261025/Receive-TIS-Transfer.ps1)와 manifest를 실제 Windows에서 보존하고, 사용자가 지정한 폴더를 로컬 인자로 전달합니다. 공개 문서에는 개인 절대 경로를 넣지 않습니다.

```powershell
.\Receive-TIS-Transfer.ps1 -Manifest .\transfer-manifest.json -ExpectedManifestSHA256 'd6fea0b0ad96e49ab434dc559af391085aa8f402bb0cf5d6c228aa57b1b65eb6' -Destination '<사용자 지정 폴더>'
```

수신기는 크기와 SHA256을 검증한 후 파일을 배치하고 실제 수신 영수증을 남깁니다. 기존 불일치 파일과 실패 partial은 보존하며 다운로드 코드를 실행하거나 압축을 해제하지 않습니다. OneDrive의 reparse point 때문에 경로가 거부될 수 있으며, 해당 Windows 경로의 실행은 시험하지 않았습니다. 설치·실행 정책·보안 설정을 바꾸지 않습니다. PowerShell 실행 환경은 이 클라우드에 없으므로 여기서 수신기를 실행했다고 주장하지 않습니다. Python 메타데이터 계약 검사 10개와 독립 소스 검토는 실제 Windows 실행 검증을 대신하지 않습니다.

[도구 설명](../../tools/windows_transfer_20261025/README.md). 실제 수신 영수증을 얻기 전에는 저장 완료로 변경하지 않습니다. 모든 전송이 통과해도 OneDrive 동기화는 별도 확인이 필요합니다.
