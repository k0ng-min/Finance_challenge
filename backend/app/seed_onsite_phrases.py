"""현지에서 화면이 쓰는 현지어 문구 시드(사람이 검수한 번역).

번역 대상은 셋뿐이다.

1. 서류명 — RequiredDocStd.doc_name (14종)
2. 요건 표시문구 — DocRequirement.label (현재 2종)
3. 창구에 보여줄 안내문 한 줄 (intro)

**조항 원문은 번역하지 않는다.** 근거 그 자체라 한국어 원문 그대로 인용한다
(models/kb.py OnsitePhraseI18n docstring 참고).

여기 담는 8개 언어는 한국인 출국자가 많은 목적지를 덮는다. 나머지 언어는
services/onsite_i18n.py가 Gemini로 만들어 같은 테이블에 캐시하고, Gemini가 없으면
한국어만 표시한다 — 기능을 막지 않는다.

서류·요건을 ID가 아니라 doc_code / label로 조회하는 이유는 seed_overlap_rules와 같다.
약관 KB를 재시드해서 ID가 바뀌어도 매핑이 어긋나지 않는다.
"""
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models.kb import DocRequirement, OnsitePhraseI18n, RequiredDocStd

LANGS = ("en", "ja", "zh", "th", "vi", "es", "fr", "de")

# doc_code -> {lang: 번역}
DOC_NAMES: dict[str, dict[str, str]] = {
    "CLAIM_FORM": {
        "en": "Insurance claim form (the insurer's own form)",
        "ja": "保険金請求書（保険会社所定の様式）",
        "zh": "保险理赔申请书（保险公司制式表格）",
        "th": "แบบฟอร์มเรียกร้องค่าสินไหมทดแทน (แบบฟอร์มของบริษัทประกัน)",
        "vi": "Đơn yêu cầu bồi thường bảo hiểm (theo mẫu của công ty bảo hiểm)",
        "es": "Formulario de reclamación del seguro (formulario de la aseguradora)",
        "fr": "Formulaire de déclaration de sinistre (formulaire de l'assureur)",
        "de": "Schadenanzeige / Leistungsantrag (Formular des Versicherers)",
    },
    "MEDICAL_EXPENSE_CERT": {
        "en": "Itemized medical bill and receipt",
        "ja": "診療費明細付きの領収書",
        "zh": "医疗费用收据（含明细）",
        "th": "ใบเสร็จรับเงินค่ารักษาพยาบาลพร้อมรายละเอียด",
        "vi": "Hóa đơn viện phí có bảng kê chi tiết",
        "es": "Factura y recibo detallados de gastos médicos",
        "fr": "Facture et reçu détaillés des frais médicaux",
        "de": "Detaillierte Arztrechnung mit Quittung",
    },
    "MEDICAL_DETAIL_CERT": {
        "en": "Detailed breakdown of medical charges",
        "ja": "診療費内訳明細書",
        "zh": "医疗费用明细清单",
        "th": "ใบแจกแจงรายละเอียดค่ารักษาพยาบาล",
        "vi": "Bảng kê chi tiết chi phí khám chữa bệnh",
        "es": "Desglose detallado de los gastos médicos",
        "fr": "Détail des frais médicaux",
        "de": "Detaillierte Aufstellung der Behandlungskosten",
    },
    "TREATMENT_CERT": {
        "en": "Certificate of hospitalization or outpatient treatment",
        "ja": "入院・通院証明書",
        "zh": "住院／门诊治疗证明书",
        "th": "ใบรับรองการรักษาผู้ป่วยในหรือผู้ป่วยนอก",
        "vi": "Giấy chứng nhận điều trị nội trú hoặc ngoại trú",
        "es": "Certificado de hospitalización o tratamiento ambulatorio",
        "fr": "Certificat d'hospitalisation ou de soins ambulatoires",
        "de": "Bescheinigung über stationäre oder ambulante Behandlung",
    },
    "PRESCRIPTION": {
        "en": "Doctor's prescription (including the pharmacy receipt)",
        "ja": "医師の処方箋（調剤費の領収書を含む）",
        "zh": "医生处方（含配药费收据）",
        "th": "ใบสั่งยาจากแพทย์ (รวมใบเสร็จค่ายา)",
        "vi": "Đơn thuốc của bác sĩ (kèm hóa đơn tiền thuốc)",
        "es": "Receta médica (incluido el recibo de la farmacia)",
        "fr": "Ordonnance du médecin (avec le reçu de la pharmacie)",
        "de": "Ärztliches Rezept (einschließlich Apothekenquittung)",
    },
    "DISABILITY_CERT": {
        "en": "Certificate of permanent disability",
        "ja": "後遺障害診断書",
        "zh": "伤残诊断证明书",
        "th": "ใบรับรองความพิการหรือทุพพลภาพถาวร",
        "vi": "Giấy chứng nhận thương tật vĩnh viễn",
        "es": "Certificado de incapacidad permanente",
        "fr": "Certificat d'invalidité permanente",
        "de": "Attest über dauerhafte Invalidität",
    },
    "DEATH_CERT": {
        "en": "Death certificate",
        "ja": "死亡診断書",
        "zh": "死亡证明书",
        "th": "ใบมรณบัตร",
        "vi": "Giấy chứng tử",
        "es": "Certificado de defunción",
        "fr": "Acte de décès",
        "de": "Sterbeurkunde",
    },
    "ID_CARD": {
        "en": "Photo identification of the claimant",
        "ja": "請求者の写真付き身分証明書",
        "zh": "索赔人带照片的身份证件",
        "th": "บัตรประจำตัวที่มีรูปถ่ายของผู้เรียกร้อง",
        "vi": "Giấy tờ tùy thân có ảnh của người yêu cầu bồi thường",
        "es": "Documento de identidad con fotografía del reclamante",
        "fr": "Pièce d'identité avec photo du demandeur",
        "de": "Lichtbildausweis der antragstellenden Person",
    },
    "THEFT_LOSS_STATEMENT": {
        "en": "Statement of loss / written account of what happened",
        "ja": "損害明細書・事故経緯書",
        "zh": "损失清单／事故经过说明书",
        "th": "รายการความเสียหาย / คำอธิบายเหตุการณ์",
        "vi": "Bảng kê thiệt hại / bản tường trình sự việc",
        "es": "Relación de daños / declaración de los hechos",
        "fr": "État des pertes / récit des circonstances du sinistre",
        "de": "Schadenaufstellung / Schilderung des Hergangs",
    },
    "POLICE_REPORT": {
        "en": "Local police report",
        "ja": "現地警察の被害届受理証明書",
        "zh": "当地警方报案证明",
        "th": "ใบแจ้งความจากสถานีตำรวจท้องที่",
        "vi": "Biên bản trình báo công an địa phương",
        "es": "Denuncia policial local",
        "fr": "Procès-verbal de dépôt de plainte auprès de la police locale",
        "de": "Polizeiliche Anzeigebestätigung vor Ort",
    },
    "FLIGHT_DELAY_CERT": {
        "en": "Flight delay or cancellation certificate issued by the airline",
        "ja": "航空機遅延・欠航証明書（航空会社発行）",
        "zh": "航班延误／取消证明（航空公司出具）",
        "th": "หนังสือรับรองเที่ยวบินล่าช้าหรือยกเลิก (ออกโดยสายการบิน)",
        "vi": "Giấy xác nhận chuyến bay chậm hoặc hủy (do hãng hàng không cấp)",
        "es": "Certificado de retraso o cancelación del vuelo emitido por la aerolínea",
        "fr": "Attestation de retard ou d'annulation de vol délivrée par la compagnie aérienne",
        "de": "Bescheinigung über Flugverspätung oder -annullierung von der Fluggesellschaft",
    },
    "BAGGAGE_IRREGULARITY": {
        "en": "Property Irregularity Report (PIR) for delayed or lost baggage",
        "ja": "手荷物事故報告書（PIR）",
        "zh": "行李运输事故报告（PIR）",
        "th": "รายงานความผิดปกติของสัมภาระ (PIR)",
        "vi": "Biên bản bất thường hành lý (PIR)",
        "es": "Parte de irregularidad de equipaje (PIR)",
        "fr": "Constat d'irrégularité bagages (PIR)",
        "de": "Property Irregularity Report (PIR) für verspätetes oder verlorenes Gepäck",
    },
    "PASSPORT_REISSUE_RECEIPT": {
        "en": "Receipt or confirmation of passport reissuance",
        "ja": "パスポート再発給の領収書・確認書",
        "zh": "护照补发收据／证明",
        "th": "ใบเสร็จหรือหนังสือรับรองการออกหนังสือเดินทางใหม่",
        "vi": "Biên lai hoặc giấy xác nhận cấp lại hộ chiếu",
        "es": "Recibo o certificado de reexpedición del pasaporte",
        "fr": "Reçu ou attestation de renouvellement du passeport",
        "de": "Quittung oder Bescheinigung über die Neuausstellung des Reisepasses",
    },
    "LIABILITY_EVIDENCE": {
        "en": "Liability documents (settlement agreement, damage claim, proof of the other party's loss)",
        "ja": "賠償責任関係書類（示談書・損害賠償請求書・相手方の被害証明書類）",
        "zh": "责任赔偿相关文件（和解协议书、索赔书、对方损失证明）",
        "th": "เอกสารเกี่ยวกับความรับผิด (หนังสือประนีประนอม หนังสือเรียกร้องค่าเสียหาย หลักฐานความเสียหายของคู่กรณี)",
        "vi": "Hồ sơ trách nhiệm dân sự (biên bản hòa giải, yêu cầu bồi thường, chứng từ thiệt hại của bên kia)",
        "es": "Documentos de responsabilidad civil (acuerdo, reclamación de daños, prueba del daño de la otra parte)",
        "fr": "Documents de responsabilité civile (accord amiable, demande d'indemnisation, justificatifs du dommage du tiers)",
        "de": "Haftpflichtunterlagen (Vergleich, Schadenersatzforderung, Schadennachweis des Geschädigten)",
    },
}

# DocRequirement.label -> {lang: 번역}
REQUIREMENT_LABELS: dict[str, dict[str, str]] = {
    "의료기관이 발급한 서류": {
        "en": "The document must be issued by a licensed medical institution.",
        "ja": "医療機関が発行した書類であること",
        "zh": "须由医疗机构出具的文件",
        "th": "เอกสารต้องออกโดยสถานพยาบาล",
        "vi": "Giấy tờ phải do cơ sở y tế cấp",
        "es": "El documento debe ser emitido por un centro médico.",
        "fr": "Le document doit être délivré par un établissement médical.",
        "de": "Das Dokument muss von einer medizinischen Einrichtung ausgestellt sein.",
    },
    "사진이 붙은 정부기관 발행 신분증": {
        "en": "Government-issued photo identification",
        "ja": "写真付きの公的機関発行の身分証明書",
        "zh": "政府机关签发的带照片身份证件",
        "th": "บัตรประจำตัวที่มีรูปถ่ายซึ่งออกโดยหน่วยงานของรัฐ",
        "vi": "Giấy tờ tùy thân có ảnh do cơ quan nhà nước cấp",
        "es": "Documento de identidad con fotografía expedido por una autoridad pública",
        "fr": "Pièce d'identité avec photo délivrée par une autorité publique",
        "de": "Amtlicher Lichtbildausweis",
    },
}

INTRO_KO = "보험 청구를 위해 아래 항목이 포함된 서류가 필요합니다. 발급을 도와주시면 감사하겠습니다."

INTRO: dict[str, str] = {
    "en": "For an insurance claim I need documents that include the items below. "
          "I would be grateful for your help in issuing them.",
    "ja": "保険金請求のため、下記の項目が記載された書類が必要です。ご発行にご協力いただけますと幸いです。",
    "zh": "我需要包含以下项目的文件用于保险理赔，烦请协助开具，谢谢。",
    "th": "ฉันต้องใช้เอกสารที่ระบุรายการด้านล่างนี้เพื่อเรียกร้องค่าสินไหมประกันภัย "
          "รบกวนช่วยออกเอกสารให้ด้วย ขอบคุณครับ/ค่ะ",
    "vi": "Tôi cần các giấy tờ có đầy đủ những mục dưới đây để làm hồ sơ yêu cầu bồi thường bảo hiểm. "
          "Rất mong quý vị hỗ trợ cấp giấy tờ. Xin cảm ơn.",
    "es": "Para una reclamación al seguro necesito documentos que incluyan los datos siguientes. "
          "Le agradecería su ayuda para emitirlos.",
    "fr": "Pour une déclaration de sinistre, j'ai besoin de documents comportant les éléments ci-dessous. "
          "Je vous remercie de votre aide pour leur délivrance.",
    "de": "Für eine Versicherungsmeldung benötige ich Unterlagen, die die unten aufgeführten Angaben "
          "enthalten. Für Ihre Hilfe bei der Ausstellung wäre ich dankbar.",
}


def _upsert(db: Session, kind: str, ref_id: int, lang: str, text: str, seen: set) -> bool:
    key = (kind, ref_id, lang)
    if key in seen:
        return False
    seen.add(key)
    db.add(OnsitePhraseI18n(kind=kind, ref_id=ref_id, lang_code=lang, text=text, source="seed"))
    return True


def seed(db: Session) -> int:
    existing = {
        (p.kind, p.ref_id, p.lang_code)
        for p in db.query(OnsitePhraseI18n).all()
    }
    added = 0

    for doc_code, by_lang in DOC_NAMES.items():
        doc = db.query(RequiredDocStd).filter(RequiredDocStd.doc_code == doc_code).first()
        if not doc:
            # 약관 KB가 아직 적재되지 않은 DB. 지어내지 않고 건너뛴다.
            continue
        for lang in LANGS:
            text = by_lang.get(lang)
            if not text:
                raise ValueError(f"{doc_code}의 {lang} 번역이 비어 있습니다.")
            if _upsert(db, OnsitePhraseI18n.KIND_DOC_NAME, doc.required_doc_std_id, lang, text, existing):
                added += 1

    for req in db.query(DocRequirement).all():
        by_lang = REQUIREMENT_LABELS.get(req.label)
        if not by_lang:
            # 새 요건이 추가됐는데 번역이 없는 경우. Gemini 경로가 런타임에 채운다.
            continue
        for lang in LANGS:
            if _upsert(db, OnsitePhraseI18n.KIND_REQUIREMENT, req.requirement_id, lang, by_lang[lang], existing):
                added += 1

    for lang in LANGS:
        if _upsert(db, OnsitePhraseI18n.KIND_INTRO, 0, lang, INTRO[lang], existing):
            added += 1

    return added


if __name__ == "__main__":
    session = SessionLocal()
    try:
        count = seed(session)
        session.commit()
        print(f"onsite_phrase_i18n {count}건 추가")
    finally:
        session.close()
