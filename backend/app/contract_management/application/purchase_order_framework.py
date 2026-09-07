"""Rattachement d'un bon de commande au contrat cadre de son fournisseur.

Partagé entre la mise à jour du bon de commande et la génération de son
document : le cadre peut avoir été signé après la dernière modification de la
mission, et le document doit tout de même en reprendre les conditions.
"""

from app.contract_management.domain.entities.purchase_order import PurchaseOrder


async def attach_framework_contract(po: PurchaseOrder, cr_repo) -> None:
    """Rattache le bon de commande au dossier cadre de son fournisseur.

    Le rattachement dépend du couple fournisseur + société émettrice : un
    cadre signé avec une société du groupe ne couvre pas une mission émise
    par une autre. Le cadre signé de la bonne société est privilégié ; à
    défaut, un dossier en cours pour cette même société est rattaché — le
    bon de commande peut être préparé pendant la contractualisation, seul
    son envoi en signature attendra.
    """
    if po.third_party_id is None:
        po.contract_request_id = None
        return

    framework = await cr_repo.get_framework_contract_for_third_party(
        po.third_party_id, po.company_id
    )
    if framework:
        po.contract_request_id = framework.id
        return

    in_progress = [
        cr
        for cr in await cr_repo.list_by_third_party(po.third_party_id)
        if cr.status.value not in ("cancelled", "redirected_payfit")
        and (po.company_id is None or cr.company_id in (po.company_id, None))
    ]
    po.contract_request_id = in_progress[0].id if in_progress else None
