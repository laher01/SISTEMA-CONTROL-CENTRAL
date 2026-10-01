RECEPTOR = "20100000001"
EMISOR = "20500000002"


def factura(
    numero: str = "F001-00000123",
    importe: str = "2500.00",
    moneda: str = "PEN",
    fecha: str = "2026-09-10",
    receptor: str = RECEPTOR,
    emisor: str = EMISOR,
) -> bytes:
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<Invoice xmlns="urn:oasis:names:specification:ubl:schema:xsd:Invoice-2"
  xmlns:cac="urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2"
  xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2">
  <cbc:UBLVersionID>2.1</cbc:UBLVersionID>
  <cbc:ID>{numero}</cbc:ID>
  <cbc:IssueDate>{fecha}</cbc:IssueDate>
  <cbc:InvoiceTypeCode listID="0101">01</cbc:InvoiceTypeCode>
  <cbc:DocumentCurrencyCode>{moneda}</cbc:DocumentCurrencyCode>
  <cac:AccountingSupplierParty><cac:Party>
    <cac:PartyIdentification><cbc:ID schemeID="6">{emisor}</cbc:ID></cac:PartyIdentification>
    <cac:PartyLegalEntity><cbc:RegistrationName>PROVEEDOR SAC</cbc:RegistrationName>
    </cac:PartyLegalEntity>
  </cac:Party></cac:AccountingSupplierParty>
  <cac:AccountingCustomerParty><cac:Party>
    <cac:PartyIdentification><cbc:ID schemeID="6">{receptor}</cbc:ID></cac:PartyIdentification>
    <cac:PartyLegalEntity><cbc:RegistrationName>CLIENTE SAC</cbc:RegistrationName>
    </cac:PartyLegalEntity>
  </cac:Party></cac:AccountingCustomerParty>
  <cac:LegalMonetaryTotal>
    <cbc:PayableAmount currencyID="{moneda}">{importe}</cbc:PayableAmount>
  </cac:LegalMonetaryTotal>
</Invoice>""".encode()


def guia(numero: str = "T001-00000045", factura_ref: str = "F001-00000123") -> bytes:
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<DespatchAdvice xmlns="urn:oasis:names:specification:ubl:schema:xsd:DespatchAdvice-2"
  xmlns:cac="urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2"
  xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2">
  <cbc:ID>{numero}</cbc:ID>
  <cbc:IssueDate>2026-09-10</cbc:IssueDate>
  <cbc:DespatchAdviceTypeCode>09</cbc:DespatchAdviceTypeCode>
  <cac:AdditionalDocumentReference>
    <cbc:ID>{factura_ref}</cbc:ID>
    <cbc:DocumentTypeCode>01</cbc:DocumentTypeCode>
  </cac:AdditionalDocumentReference>
  <cac:DespatchSupplierParty><cac:Party>
    <cac:PartyIdentification><cbc:ID schemeID="6">{EMISOR}</cbc:ID></cac:PartyIdentification>
  </cac:Party></cac:DespatchSupplierParty>
  <cac:DeliveryCustomerParty><cac:Party>
    <cac:PartyIdentification><cbc:ID schemeID="6">{RECEPTOR}</cbc:ID></cac:PartyIdentification>
  </cac:Party></cac:DeliveryCustomerParty>
</DespatchAdvice>""".encode()
