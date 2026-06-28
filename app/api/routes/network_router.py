import ipaddress

from fastapi import APIRouter, Depends, HTTPException

from app.api.shémas import (
    ACLRequestInput,
    SiteDiscoveryRequest,
    VLANRequestInput,
    VLSMInput,
    NetworkRenderInput,
    DeployRequest
)

from app.database.database import (
    add_log,
    save_acls,
    save_vlsm_to_db,
    build_device_map,
    save_architecture_report
)

from app.services.notification_service import create_notification

from core.architecture_detector.full_architecture import build_site_report
from core.vlan.generate_vlans_vlsm import generate_vlsm_detailed
from core.vlan_detection.detect_vlan import process_vlan_requests
from core.acl.generate_ACL import process_acl_policies

from core.gestion_utilisateurs.security import require_permission
from app.services.discovery_db_service import save_discovery_report_to_db
from app.services.save_vlan_db_service import save_vlan_result_to_db

from core.generator.vlan_generator import (
    render_network_configs_per_device,
    save_network_configs_to_files,
    render_config_from_final_plan
)

from core.generator.acl_generator import (
    render_acl_configs_per_device,
    save_acl_configs_to_files
)

from core.deploy.check_configs import check_network_config_files
from core.deploy.check_ACL_configs import check_acl_config_files
from core.deploy.inventory_builder import build_inventory
from core.deploy.deployer import run_deployment
from core.deploy.deploy_config import run_network_deployment

from app.websocket.manager import send_notification


router = APIRouter(tags=["Network"])


def safe_create_notification(user_id: int, title: str, message: str, type: str = "info"):
    try:
        create_notification(
            user_id=user_id,
            title=title,
            message=message,
            type=type
        )
    except Exception as e:
        print("Notification DB/Email failed:", e)


@router.post("/network/site")
async def discover_site(
    data: SiteDiscoveryRequest,
    current_user: dict = Depends(require_permission("discover_site"))
):
    try:
        report = build_site_report(
            seed_device=data.seed_device.dict(),
            site_name=data.site_name
        )

        db_result = save_discovery_report_to_db(
            report=report,
            user_id=current_user["id"]
        )

        architecture_report_id = save_architecture_report(
            user_id=current_user["id"],
            site_name=data.site_name,
            report=report
        )

        await send_notification(
            user_id=current_user["id"],
            message=f"Découverte terminée pour {data.site_name}",
            type="INFO",
            hostname=data.seed_device.hostname
        )

        safe_create_notification(
            user_id=current_user["id"],
            title="Découverte réseau terminée",
            message=f"Découverte terminée pour {data.site_name}.",
            type="info"
        )

        devices = report.get("topology", {}).get("devices", [])

        for device in devices:
            if device.get("reachable") is False:
                await send_notification(
                    user_id=current_user["id"],
                    message=f"{device.get('hostname')} est non joignable",
                    type="CRITICAL",
                    hostname=device.get("hostname")
                )

                safe_create_notification(
                    user_id=current_user["id"],
                    title="Équipement non joignable",
                    message=f"{device.get('hostname')} est non joignable.",
                    type="critical"
                )

        add_log(
            action="DISCOVER_SITE_SUCCESS",
            device_id=None,
            user_id=current_user["id"],
            module="DISCOVERY",
            status="success",
            extra={
                "site_name": data.site_name,
                "device_count": report.get("summary", {}).get("device_count", 0),
                "link_count": len(report.get("topology", {}).get("links", [])),
                "saved_devices": db_result.get("saved_devices", 0),
                "saved_links": db_result.get("saved_links", 0),
                "saved_vlans": db_result.get("saved_vlans", 0),
                "report_id": db_result.get("report_id"),
                "architecture_report_id": architecture_report_id,
                "file_path": db_result.get("file_path")
            }
        )

        return {
            "status": "success",
            "message": "LAN discovered successfully",
            "report": report,
            "database": db_result,
            "architecture_report": {
                "saved": True,
                "id": architecture_report_id,
                "site_name": data.site_name
            }
        }

    except Exception as e:
        try:
            await send_notification(
                user_id=current_user["id"],
                message=f"Échec découverte réseau pour {data.site_name}",
                type="CRITICAL",
                hostname=data.seed_device.hostname
            )

            safe_create_notification(
                user_id=current_user["id"],
                title="Échec découverte réseau",
                message=f"Échec découverte réseau pour {data.site_name}: {str(e)}",
                type="critical"
            )

            add_log(
                action="DISCOVER_SITE_FAILED",
                device_id=None,
                user_id=current_user["id"],
                module="DISCOVERY",
                status="failed",
                extra={
                    "site_name": data.site_name,
                    "seed_ip": data.seed_device.ip,
                    "error": str(e)
                }
            )
        except Exception:
            pass

        raise HTTPException(
            status_code=500,
            detail=f"Discovery failed: {str(e)}"
        )


@router.post("/generate-vlan")
def generate_vlan_endpoint(
    data: VLANRequestInput,
    current_user: dict = Depends(require_permission("create_vlan"))
):
    response = {
        "status": "success",
        "user_id": current_user["id"],
        "steps": [],
        "errors": [],
        "warnings": [],
        "vlan_result": {},
        "database": {}
    }

    try:
        vlan_result = process_vlan_requests(
            report=data.report,
            requested_zones=[item.dict() for item in data.requested_zones]
        )

        response["vlan_result"] = vlan_result
        response["errors"].extend(vlan_result.get("errors", []))

        response["steps"].append({
            "step": "process_vlan_requests",
            "status": "success",
            "created": len(vlan_result.get("created", [])),
            "skipped": len(vlan_result.get("skipped", []))
        })

        device_map = build_device_map()

        db_result = save_vlan_result_to_db(
            vlan_result=vlan_result,
            device_map=device_map
        )

        response["database"] = db_result

        response["steps"].append({
            "step": "save_db",
            "status": "success" if not db_result["errors"] else "partial_success",
            "saved_vlans": db_result["saved_vlans"]
        })

        add_log(
            action="GENERATE_VLAN",
            device_id=None,
            user_id=current_user["id"],
            module="VLAN",
            status="success" if not response["errors"] else "partial_success",
            extra={
                "created": len(vlan_result.get("created", [])),
                "skipped": len(vlan_result.get("skipped", [])),
                "saved_vlans": db_result.get("saved_vlans", 0),
                "db_errors": db_result.get("errors", []),
                "errors": vlan_result.get("errors", [])
            }
        )

        safe_create_notification(
            user_id=current_user["id"],
            title="Génération VLAN terminée",
            message=f"{len(vlan_result.get('created', []))} VLAN(s) généré(s), {len(vlan_result.get('skipped', []))} ignoré(s).",
            type="info" if not response["errors"] else "warning"
        )

    except Exception as e:
        response["status"] = "failed"
        response["errors"].append(str(e))

        try:
            add_log(
                action="GENERATE_VLAN",
                device_id=None,
                user_id=current_user["id"],
                module="VLAN",
                status="failed",
                extra={"error": str(e)}
            )

            safe_create_notification(
                user_id=current_user["id"],
                title="Échec génération VLAN",
                message=str(e),
                type="error"
            )
        except Exception:
            pass

        raise HTTPException(status_code=500, detail=str(e))

    response["summary"] = {
        "created_count": len(response["vlan_result"].get("created", [])) if response["vlan_result"] else 0,
        "skipped_count": len(response["vlan_result"].get("skipped", [])) if response["vlan_result"] else 0,
        "saved_vlans": response["database"].get("saved_vlans", 0),
        "error_count": len(response["errors"])
    }

    return response


@router.post("/network/generate-vlsm")
def generate_vlsm_endpoint(
    data: VLSMInput,
    current_user: dict = Depends(require_permission("generate_vlsm"))
):
    report_response = {
        "status": "success",
        "user_id": current_user["id"],
        "steps": [],
        "errors": [],
        "warnings": [],
        "vlsm": {}
    }

    try:
        vlsm_result = generate_vlsm_detailed(
            report=data.report,
            base_network=data.base_network,
            requirements=[req.dict() for req in data.requirements]
        )

        report_response["steps"].append({
            "step": "generate_vlsm",
            "status": "success",
            "count": len(vlsm_result.get("planned_subnets", []))
        })

    except Exception as e:
        report_response["steps"].append({
            "step": "generate_vlsm",
            "status": "failed",
            "error": str(e)
        })
        report_response["errors"].append(str(e))
        report_response["status"] = "failed"

        add_log(
            action="GENERATE_VLSM",
            device_id=None,
            user_id=current_user["id"],
            module="VLSM",
            status="failed",
            extra={
                "base_network": data.base_network,
                "error": str(e)
            }
        )

        safe_create_notification(
            user_id=current_user["id"],
            title="Échec génération VLSM",
            message=str(e),
            type="error"
        )

        return report_response

    try:
        base_net = ipaddress.ip_network(data.base_network, strict=False)
        warnings_count = 0

        for item in vlsm_result.get("planned_subnets", []):
            if item.get("status") != "planned":
                continue

            subnet = ipaddress.ip_network(item["subnet"], strict=False)

            if not subnet.subnet_of(base_net):
                report_response["warnings"].append(
                    f"{item['subnet']} hors du réseau de base"
                )
                warnings_count += 1

        add_log(
            action="VALIDATE_VLSM",
            device_id=None,
            user_id=current_user["id"],
            module="VLSM",
            status="success",
            extra={"warnings": warnings_count}
        )

    except Exception as e:
        report_response["warnings"].append(f"validation skipped: {str(e)}")

    try:
        planned_only = [
            {
                "id": item["id"],
                "departement": item["departement"],
                "subnet": item["subnet"],
                "mask": item["mask"],
                "gateway": item["gateway"],
                "broadcast": item["broadcast"],
                "usable_hosts": item["usable_hosts"]
            }
            for item in vlsm_result.get("planned_subnets", [])
            if item.get("status") == "planned"
        ]

        save_vlsm_to_db(planned_only)

        report_response["steps"].append({
            "step": "save_db",
            "status": "success",
            "saved": len(planned_only)
        })

        safe_create_notification(
            user_id=current_user["id"],
            title="Plan VLSM généré",
            message=f"{len(planned_only)} sous-réseau(x) planifié(s) et sauvegardé(s).",
            type="info" if not report_response["warnings"] else "warning"
        )

    except Exception as e:
        report_response["steps"].append({
            "step": "save_db",
            "status": "failed",
            "error": str(e)
        })
        report_response["errors"].append(str(e))

        safe_create_notification(
            user_id=current_user["id"],
            title="Échec sauvegarde VLSM",
            message=str(e),
            type="error"
        )

    report_response["vlsm"] = vlsm_result
    report_response["summary"] = {
        "requested_zone_count": len(data.requirements),
        "planned_zone_count": len([
            x for x in vlsm_result.get("planned_subnets", [])
            if x.get("status") == "planned"
        ]),
        "skipped_zone_count": len(vlsm_result.get("skipped_zones", [])),
        "total_requested_hosts": sum(req.required_hosts for req in data.requirements)
    }

    add_log(
        action="GENERATE_VLSM",
        device_id=None,
        user_id=current_user["id"],
        module="VLSM",
        status=report_response["status"],
        extra={
            "base_network": data.base_network,
            "requested_zone_count": len(data.requirements),
            "planned_zone_count": report_response["summary"]["planned_zone_count"],
            "skipped_zone_count": report_response["summary"]["skipped_zone_count"],
            "error_count": len(report_response["errors"]),
            "warning_count": len(report_response["warnings"])
        }
    )

    return report_response


@router.post("/generate-acl")
def generate_acl_endpoint(
    data: ACLRequestInput,
    current_user: dict = Depends(require_permission("generate_acl"))
):
    response = {
        "status": "success",
        "user_id": current_user["id"],
        "steps": [],
        "errors": [],
        "warnings": [],
        "acl_result": {},
        "database": {}
    }

    try:
        acl_result = process_acl_policies(
            report=data.report,
            policies=[policy.dict() for policy in data.policies]
        )

        response["acl_result"] = acl_result
        response["errors"].extend(acl_result.get("errors", []))

        response["steps"].append({
            "step": "process_acl_policies",
            "status": "success",
            "created": len(acl_result.get("created", [])),
            "updated": len(acl_result.get("updated", [])),
            "deleted": len(acl_result.get("deleted", []))
        })

        acls_to_save = []

        for item in acl_result.get("created", []):
            for rule in item.get("rules", []):
                acls_to_save.append({
                    "device": item.get("device"),
                    "acl_name": item.get("acl_name"),
                    "action": rule.get("action"),
                    "protocol": rule.get("protocol"),
                    "source": rule.get("source"),
                    "destination": rule.get("destination"),
                    "port": rule.get("port")
                })

        for item in acl_result.get("updated", []):
            for rule in item.get("new_rules", []):
                acls_to_save.append({
                    "device": item.get("device"),
                    "acl_name": item.get("acl_name"),
                    "action": rule.get("action"),
                    "protocol": rule.get("protocol"),
                    "source": rule.get("source"),
                    "destination": rule.get("destination"),
                    "port": rule.get("port")
                })

        device_map = build_device_map()
        save_acls(acls_to_save, device_map)

        response["database"] = {
            "saved_rules": len(acls_to_save)
        }

        response["steps"].append({
            "step": "save_db",
            "status": "success",
            "saved_rules": len(acls_to_save)
        })

        add_log(
            action="GENERATE_ACL",
            device_id=None,
            user_id=current_user["id"],
            module="ACL",
            status="success" if not response["errors"] else "partial_success",
            extra={
                "created": len(acl_result.get("created", [])),
                "updated": len(acl_result.get("updated", [])),
                "deleted": len(acl_result.get("deleted", [])),
                "saved_rules": len(acls_to_save),
                "errors": acl_result.get("errors", [])
            }
        )

        safe_create_notification(
            user_id=current_user["id"],
            title="ACL générées",
            message=f"{len(acls_to_save)} règle(s) ACL sauvegardée(s).",
            type="info" if not response["errors"] else "warning"
        )

    except Exception as e:
        response["status"] = "failed"
        response["errors"].append(str(e))

        try:
            add_log(
                action="GENERATE_ACL",
                device_id=None,
                user_id=current_user["id"],
                module="ACL",
                status="failed",
                extra={"error": str(e)}
            )

            safe_create_notification(
                user_id=current_user["id"],
                title="Échec génération ACL",
                message=str(e),
                type="error"
            )
        except Exception:
            pass

        raise HTTPException(status_code=500, detail=str(e))

    response["summary"] = {
        "created_count": len(response["acl_result"].get("created", [])),
        "updated_count": len(response["acl_result"].get("updated", [])),
        "deleted_count": len(response["acl_result"].get("deleted", [])),
        "saved_rules": response["database"].get("saved_rules", 0),
        "error_count": len(response["errors"])
    }

    return response


@router.post("/render-network")
def render_network_final_endpoint(
    data: NetworkRenderInput,
    current_user: dict = Depends(require_permission("generate_vlsm"))
):
    response = {
        "status": "success",
        "user_id": current_user["id"],
        "steps": [],
        "errors": [],
        "vlan_result": {},
        "vlsm_result": {},
        "rendered_configs": {},
        "saved_files": {}
    }

    try:
        vlan_result = process_vlan_requests(
            report=data.report,
            requested_zones=[item.dict() for item in data.requested_zones]
        )

        response["vlan_result"] = vlan_result

        response["steps"].append({
            "step": "process_vlan_requests",
            "status": "success",
            "created": len(vlan_result.get("created", [])),
            "skipped": len(vlan_result.get("skipped", []))
        })

        vlsm_result = generate_vlsm_detailed(
            report=data.report,
            base_network=data.base_network,
            requirements=[item.dict() for item in data.requirements]
        )

        response["vlsm_result"] = vlsm_result

        response["steps"].append({
            "step": "generate_vlsm",
            "status": "success",
            "planned": len(vlsm_result.get("planned_subnets", []))
        })

        if getattr(data, "final_plan", None):
            rendered_configs = render_config_from_final_plan(
                final_plan=data.final_plan,
                report=data.report
            )

            response["steps"].append({
                "step": "render_from_final_plan",
                "status": "success",
                "device_count": len(rendered_configs)
            })

        else:
            rendered_configs = render_network_configs_per_device(
                vlan_result=vlan_result,
                vlsm_result=vlsm_result
            )

            response["steps"].append({
                "step": "render_jinja2",
                "status": "success",
                "device_count": len(rendered_configs)
            })

        # Correction automatique : si une config contient des SVI,
        # alors l'équipement doit être considéré comme SITE_CORE
        # et doit contenir ip routing.
        fixed_configs = {}

        for hostname, config in rendered_configs.items():
            if "interface Vlan" in config:
                config = config.replace(
                    "! ROLE: ACCESS_SWITCH",
                    "! ROLE: SITE_CORE"
                )

                if "ip routing" not in config:
                    marker = "! -------- VLAN CREATION --------"
                    config = config.replace(
                        marker,
                        "! -------- INTER-VLAN ROUTING --------\n"
                        "ip routing\n"
                        "!\n\n"
                        f"{marker}"
                    )

            if "switchport mode trunk" in config and "switchport trunk encapsulation dot1q" not in config:
                config = config.replace(
                    " switchport mode trunk",
                    " switchport trunk encapsulation dot1q\n switchport mode trunk"
                )

            fixed_configs[hostname] = config

        rendered_configs = fixed_configs

        response["rendered_configs"] = rendered_configs

        saved_files = save_network_configs_to_files(rendered_configs)
        response["saved_files"] = saved_files

        response["steps"].append({
            "step": "save_cfg_files",
            "status": "success",
            "file_count": len(saved_files)
        })

        add_log(
            action="RENDER_NETWORK_CONFIG_FINAL",
            device_id=None,
            user_id=current_user["id"],
            module="GENERATOR",
            status="success",
            extra={
                "device_count": len(rendered_configs),
                "file_count": len(saved_files),
                "used_final_plan": bool(getattr(data, "final_plan", None))
            }
        )

        safe_create_notification(
            user_id=current_user["id"],
            title="Configuration réseau générée",
            message=f"{len(rendered_configs)} configuration(s) générée(s), {len(saved_files)} fichier(s) sauvegardé(s).",
            type="info"
        )

    except Exception as e:
        response["status"] = "failed"
        response["errors"].append(str(e))

        try:
            add_log(
                action="RENDER_NETWORK_CONFIG_FINAL",
                device_id=None,
                user_id=current_user["id"],
                module="GENERATOR",
                status="failed",
                extra={"error": str(e)}
            )

            safe_create_notification(
                user_id=current_user["id"],
                title="Échec génération configuration réseau",
                message=str(e),
                type="error"
            )
        except Exception:
            pass

        raise HTTPException(status_code=500, detail=str(e))

    return response

@router.post("/render-acl")
def render_acl_endpoint(
    data: ACLRequestInput,
    current_user: dict = Depends(require_permission("generate_acl"))
):
    response = {
        "status": "success",
        "user_id": current_user["id"],
        "steps": [],
        "errors": [],
        "acl_result": {},
        "rendered_configs": {},
        "saved_files": {}
    }

    try:
        acl_result = process_acl_policies(
            report=data.report,
            policies=[item.dict() for item in data.policies]
        )

        response["acl_result"] = acl_result
        response["errors"].extend(acl_result.get("errors", []))

        response["steps"].append({
            "step": "process_acl_policies",
            "status": "success",
            "created": len(acl_result.get("created", [])),
            "updated": len(acl_result.get("updated", [])),
            "deleted": len(acl_result.get("deleted", []))
        })

        rendered_configs = render_acl_configs_per_device(acl_result)
        response["rendered_configs"] = rendered_configs

        response["steps"].append({
            "step": "render_jinja2",
            "status": "success",
            "device_count": len(rendered_configs)
        })

        saved_files = save_acl_configs_to_files(rendered_configs)
        response["saved_files"] = saved_files

        response["steps"].append({
            "step": "save_cfg_files",
            "status": "success",
            "file_count": len(saved_files)
        })

        add_log(
            action="RENDER_ACL_CONFIG",
            device_id=None,
            user_id=current_user["id"],
            module="ACL",
            status="success",
            extra={
                "device_count": len(rendered_configs),
                "file_count": len(saved_files)
            }
        )

        safe_create_notification(
            user_id=current_user["id"],
            title="Configuration ACL générée",
            message=f"{len(rendered_configs)} configuration(s) ACL générée(s).",
            type="info" if not response["errors"] else "warning"
        )

    except Exception as e:
        response["status"] = "failed"
        response["errors"].append(str(e))

        add_log(
            action="RENDER_ACL_CONFIG",
            device_id=None,
            user_id=current_user["id"],
            module="ACL",
            status="failed",
            extra={"error": str(e)}
        )

        safe_create_notification(
            user_id=current_user["id"],
            title="Échec rendu ACL",
            message=str(e),
            type="error"
        )

        raise HTTPException(status_code=500, detail=str(e))

    return response


@router.post("/deploy-network")
def deploy_network_configs_endpoint(
    data: DeployRequest,
    current_user: dict = Depends(require_permission("deploy_configs"))
):
    response = {
        "status": "success",
        "user_id": current_user["id"],
        "steps": [],
        "errors": [],
        "inventory_file": None,
        "checked_files": {},
        "deployment_result": {}
    }

    try:
        devices = [item.dict() for item in data.devices]

        checked = check_network_config_files(devices, config_folder="output/configs")
        response["checked_files"] = checked

        if checked["missing"]:
            response["status"] = "failed"
            response["errors"].append(
                f"Missing network config files for: {', '.join(checked['missing'])}"
            )

            add_log(
                action="DEPLOY_NETWORK_CONFIGS",
                device_id=None,
                user_id=current_user["id"],
                module="DEPLOYMENT",
                status="failed",
                extra={
                    "reason": "missing_config_files",
                    "missing": checked["missing"]
                }
            )

            safe_create_notification(
                user_id=current_user["id"],
                title="Déploiement réseau impossible",
                message=f"Fichiers config manquants pour: {', '.join(checked['missing'])}",
                type="critical"
            )

            return response

        response["steps"].append({
            "step": "check_network_cfg_files",
            "status": "success",
            "file_count": len(checked["existing"])
        })

        inventory_file = build_inventory(devices)
        response["inventory_file"] = inventory_file

        response["steps"].append({
            "step": "build_inventory",
            "status": "success"
        })

        deployment_result = run_network_deployment()
        response["deployment_result"] = deployment_result

        response["steps"].append({
            "step": "run_network_ansible",
            "status": deployment_result["status"],
            "return_code": deployment_result["return_code"]
        })

        if deployment_result["status"] != "success":
            response["status"] = "failed"
            response["errors"].append("Network deployment failed")

        add_log(
            action="DEPLOY_NETWORK_CONFIGS",
            device_id=None,
            user_id=current_user["id"],
            module="DEPLOYMENT",
            status=response["status"],
            extra={
                "device_count": len(devices),
                "return_code": deployment_result["return_code"]
            }
        )

        safe_create_notification(
            user_id=current_user["id"],
            title="Déploiement réseau terminé" if response["status"] == "success" else "Déploiement réseau échoué",
            message=f"Déploiement réseau terminé avec statut: {response['status']}.",
            type="info" if response["status"] == "success" else "critical"
        )

    except Exception as e:
        add_log(
            action="DEPLOY_NETWORK_CONFIGS",
            device_id=None,
            user_id=current_user["id"],
            module="DEPLOYMENT",
            status="failed",
            extra={"error": str(e)}
        )

        safe_create_notification(
            user_id=current_user["id"],
            title="Erreur déploiement réseau",
            message=str(e),
            type="critical"
        )

        raise HTTPException(status_code=500, detail=str(e))

    return response


@router.post("/deploy-acl-configs")
def deploy_acl_configs_endpoint(
    data: DeployRequest,
    current_user: dict = Depends(require_permission("deploy_configs"))
):
    response = {
        "status": "success",
        "user_id": current_user["id"],
        "steps": [],
        "errors": [],
        "inventory_file": None,
        "checked_files": {},
        "deployment_result": {}
    }

    try:
        devices = [item.dict() for item in data.devices]

        checked = check_acl_config_files(devices, config_folder="output/acl_configs")
        response["checked_files"] = checked

        if checked["missing"]:
            response["status"] = "failed"
            response["errors"].append(
                f"Missing ACL config files for: {', '.join(checked['missing'])}"
            )

            add_log(
                action="DEPLOY_ACL_CONFIGS",
                device_id=None,
                user_id=current_user["id"],
                module="DEPLOYMENT",
                status="failed",
                extra={
                    "reason": "missing_acl_config_files",
                    "missing": checked["missing"]
                }
            )

            safe_create_notification(
                user_id=current_user["id"],
                title="Déploiement ACL impossible",
                message=f"Fichiers ACL manquants pour: {', '.join(checked['missing'])}",
                type="critical"
            )

            return response

        response["steps"].append({
            "step": "check_acl_cfg_files",
            "status": "success",
            "file_count": len(checked["existing"])
        })

        inventory_file = build_inventory(devices)
        response["inventory_file"] = inventory_file

        response["steps"].append({
            "step": "build_inventory",
            "status": "success"
        })

        deployment_result = run_deployment()
        response["deployment_result"] = deployment_result

        response["steps"].append({
            "step": "run_acl_ansible",
            "status": deployment_result["status"],
            "return_code": deployment_result["return_code"]
        })

        if deployment_result["status"] != "success":
            response["status"] = "failed"
            response["errors"].append("ACL deployment failed")

        add_log(
            action="DEPLOY_ACL_CONFIGS",
            device_id=None,
            user_id=current_user["id"],
            module="DEPLOYMENT",
            status=response["status"],
            extra={
                "device_count": len(devices),
                "return_code": deployment_result["return_code"]
            }
        )

        safe_create_notification(
            user_id=current_user["id"],
            title="Déploiement ACL terminé" if response["status"] == "success" else "Déploiement ACL échoué",
            message=f"Déploiement ACL terminé avec statut: {response['status']}.",
            type="info" if response["status"] == "success" else "critical"
        )

    except Exception as e:
        add_log(
            action="DEPLOY_ACL_CONFIGS",
            device_id=None,
            user_id=current_user["id"],
            module="DEPLOYMENT",
            status="failed",
            extra={"error": str(e)}
        )

        safe_create_notification(
            user_id=current_user["id"],
            title="Erreur déploiement ACL",
            message=str(e),
            type="critical"
        )

        raise HTTPException(status_code=500, detail=str(e))

    return response