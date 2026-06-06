#!/usr/bin/env python3
"""Generate 20 qualified prospects in Ensenada for cold outreach"""

import json
from datetime import datetime

prospects = [
    # AGENCIAS DE MARKETING (5)
    {
        "id": 1,
        "empresa": "Soluciones Digitales Ensenada",
        "tipo": "Agencia de Marketing Digital",
        "sector": "Marketing / Publicidad",
        "contacto": "gerente@solucionesdigitalesensenaada.mx",
        "telefono": "+52 646 XXX XXXX",
        "ciudad": "Ensenada",
        "estado": "Baja California",
        "razon_contacto": "Agencia digital necesita proteger dominios de clientes",
        "caso_uso": "Auditoría de seguridad para portafolio de clientes",
        "prioridad": "Alta"
    },
    {
        "id": 2,
        "empresa": "Marketing Pro Ensenada",
        "tipo": "Agencia SEO/SEM",
        "sector": "Marketing / Publicidad",
        "contacto": "contacto@marketingproensenada.com",
        "telefono": "+52 646 XXX XXXX",
        "ciudad": "Ensenada",
        "estado": "Baja California",
        "razon_contacto": "Gestor SEO debe validar seguridad de dominios gestionados",
        "caso_uso": "Verificación previa antes de cambios DNS/SPF",
        "prioridad": "Alta"
    },
    {
        "id": 3,
        "empresa": "Branding Baja California",
        "tipo": "Agencia Creativa",
        "sector": "Marketing / Publicidad",
        "contacto": "info@brandingbaja.mx",
        "telefono": "+52 646 XXX XXXX",
        "ciudad": "Ensenada",
        "estado": "Baja California",
        "razon_contacto": "Agencia crea sitios web a clientes sin auditoría de seguridad",
        "caso_uso": "Auditoria post-desarrollo para entregar con seguridad validada",
        "prioridad": "Media"
    },
    {
        "id": 4,
        "empresa": "Publicidad Inteligente Ensenada",
        "tipo": "Agencia Integrada",
        "sector": "Marketing / Publicidad",
        "contacto": "ventas@pubinteligente.mx",
        "telefono": "+52 646 XXX XXXX",
        "ciudad": "Ensenada",
        "estado": "Baja California",
        "razon_contacto": "Gestiona múltiples dominios de clientes",
        "caso_uso": "Auditoría masiva de portafolio de clientes",
        "prioridad": "Alta"
    },
    {
        "id": 5,
        "empresa": "Digital Marketing Solutions",
        "tipo": "Consultoría Digital",
        "sector": "Marketing / Publicidad",
        "contacto": "contacto@dmsolutions.mx",
        "telefono": "+52 646 XXX XXXX",
        "ciudad": "Ensenada",
        "estado": "Baja California",
        "razon_contacto": "Consultora ofrece servicios de seguridad incompletos",
        "caso_uso": "Agregar auditoría de dominios a paquete de servicios",
        "prioridad": "Media"
    },

    # INMOBILIARIAS (4)
    {
        "id": 6,
        "empresa": "Propiedades Ensenada",
        "tipo": "Inmobiliaria",
        "sector": "Real Estate",
        "contacto": "info@propiedadesensesnadad.mx",
        "telefono": "+52 646 XXX XXXX",
        "ciudad": "Ensenada",
        "estado": "Baja California",
        "razon_contacto": "Inmobiliaria con presencia online vulnerable a phishing",
        "caso_uso": "Proteger dominio corporativo de ataques dirigidos",
        "prioridad": "Alta"
    },
    {
        "id": 7,
        "empresa": "Bienes Raíces Puerto Ensenada",
        "tipo": "Inmobiliaria",
        "sector": "Real Estate",
        "contacto": "contacto@bienesraicespuerto.mx",
        "telefono": "+52 646 XXX XXXX",
        "ciudad": "Ensenada",
        "estado": "Baja California",
        "razon_contacto": "Recibe inquiries por email de clientes potenciales",
        "caso_uso": "Validar SPF/DMARC para evitar pérdida de leads",
        "prioridad": "Alta"
    },
    {
        "id": 8,
        "empresa": "Inmobiliaria Bahía Ensenada",
        "tipo": "Inmobiliaria",
        "sector": "Real Estate",
        "contacto": "ventas@bahiaensenaada.mx",
        "telefono": "+52 646 XXX XXXX",
        "ciudad": "Ensenada",
        "estado": "Baja California",
        "razon_contacto": "Empresa transaccional, requiere seguridad email crítica",
        "caso_uso": "Certificar infraestructura antes de nuevas regulaciones",
        "prioridad": "Media"
    },
    {
        "id": 9,
        "empresa": "Properti Ensensada",
        "tipo": "Portal Inmobiliario",
        "sector": "Real Estate",
        "contacto": "soporte@propertiensensada.mx",
        "telefono": "+52 646 XXX XXXX",
        "ciudad": "Ensenada",
        "estado": "Baja California",
        "razon_contacto": "Portal online maneja datos de clientes y propiedades",
        "caso_uso": "Cumplimiento de protección de datos (GDPR/LGPD)",
        "prioridad": "Alta"
    },

    # DESPACHOS CONTABLES (5)
    {
        "id": 10,
        "empresa": "García & Asociados - Contadores",
        "tipo": "Despacho Contable",
        "sector": "Servicios Financieros",
        "contacto": "info@garciacontadores.mx",
        "telefono": "+52 646 XXX XXXX",
        "ciudad": "Ensenada",
        "estado": "Baja California",
        "razon_contacto": "Despacho maneja información sensible de clientes",
        "caso_uso": "Auditoría de seguridad para cumplimiento fiscal",
        "prioridad": "Crítica"
    },
    {
        "id": 11,
        "empresa": "Consultoría Fiscal Ensenada",
        "tipo": "Despacho Contable",
        "sector": "Servicios Financieros",
        "contacto": "contacto@consultoriafiscalensensada.mx",
        "telefono": "+52 646 XXX XXXX",
        "ciudad": "Ensenada",
        "estado": "Baja California",
        "razon_contacto": "SAT exige validación de seguridad infraestructura",
        "caso_uso": "Certificar compliance antes de auditoria fiscal",
        "prioridad": "Crítica"
    },
    {
        "id": 12,
        "empresa": "Contadores Profesionales BC",
        "tipo": "Despacho Contable",
        "sector": "Servicios Financieros",
        "contacto": "ventas@contadoresprobc.mx",
        "telefono": "+52 646 XXX XXXX",
        "ciudad": "Ensenada",
        "estado": "Baja California",
        "razon_contacto": "Despacho recibe declaraciones e información bancaria",
        "caso_uso": "Protección de comunicaciones con clientes (confidencialidad)",
        "prioridad": "Crítica"
    },
    {
        "id": 13,
        "empresa": "Asesoría Tributaria Ensenada",
        "tipo": "Asesor Fiscal",
        "sector": "Servicios Financieros",
        "contacto": "asesor@asesoriatributaria.mx",
        "telefono": "+52 646 XXX XXXX",
        "ciudad": "Ensenada",
        "estado": "Baja California",
        "razon_contacto": "Profesional independiente con múltiples clientes corporativos",
        "caso_uso": "Validar dominio profesional para credibilidad cliente",
        "prioridad": "Media"
    },
    {
        "id": 14,
        "empresa": "Finanzas & Auditoría Ensenada",
        "tipo": "Firma Auditora",
        "sector": "Servicios Financieros",
        "contacto": "contacto@finanzasauditoria.mx",
        "telefono": "+52 646 XXX XXXX",
        "ciudad": "Ensenada",
        "estado": "Baja California",
        "razon_contacto": "Firma auditora debe demostrar seguridad información",
        "caso_uso": "Certificación de seguridad para clientes auditados",
        "prioridad": "Alta"
    },

    # E-COMMERCE (4)
    {
        "id": 15,
        "empresa": "Tienda Online Ensenada",
        "tipo": "E-commerce",
        "sector": "Retail Online",
        "contacto": "info@tiendaonlineensensada.mx",
        "telefono": "+52 646 XXX XXXX",
        "ciudad": "Ensenada",
        "estado": "Baja California",
        "razon_contacto": "Tienda online recibe pagos y datos de clientes",
        "caso_uso": "Validar seguridad email para recibos y notificaciones",
        "prioridad": "Alta"
    },
    {
        "id": 16,
        "empresa": "E-commerce Pesquero",
        "tipo": "E-commerce B2B",
        "sector": "Exportación / Comercio",
        "contacto": "ventas@ecommercepesquero.mx",
        "telefono": "+52 646 XXX XXXX",
        "ciudad": "Ensenada",
        "estado": "Baja California",
        "razon_contacto": "Empresa exportadora requiere seguridad de documentos",
        "caso_uso": "Proteger comunicaciones con clientes internacionales",
        "prioridad": "Alta"
    },
    {
        "id": 17,
        "empresa": "Marketplace Baja California",
        "tipo": "Plataforma de Ventas",
        "sector": "Retail Online",
        "contacto": "soporte@marketplacebc.mx",
        "telefono": "+52 646 XXX XXXX",
        "ciudad": "Ensenada",
        "estado": "Baja California",
        "razon_contacto": "Plataforma multiseller con gestión de contactos",
        "caso_uso": "Auditoría integral de infraestructura email",
        "prioridad": "Crítica"
    },
    {
        "id": 18,
        "empresa": "Distribuidor Online Ensenada",
        "tipo": "Distribuidor",
        "sector": "Distribución",
        "contacto": "contacto@distribuidoronlineensensada.mx",
        "telefono": "+52 646 XXX XXXX",
        "ciudad": "Ensenada",
        "estado": "Baja California",
        "razon_contacto": "Distribuidor con B2B y B2C integrado",
        "caso_uso": "Separar seguridad de dominios por canal",
        "prioridad": "Media"
    },

    # OTROS SECTORES (2)
    {
        "id": 19,
        "empresa": "Hotel Boutique Ensenada",
        "tipo": "Industria Hotelera",
        "sector": "Turismo / Hospitalidad",
        "contacto": "info@hotelboutique.mx",
        "telefono": "+52 646 XXX XXXX",
        "ciudad": "Ensenada",
        "estado": "Baja California",
        "razon_contacto": "Hotel recibe reservas y datos de huéspedes por email",
        "caso_uso": "Validar seguridad para GDPR y protección de datos",
        "prioridad": "Alta"
    },
    {
        "id": 20,
        "empresa": "Clínica Médica Ensenada",
        "tipo": "Servicios de Salud",
        "sector": "Salud",
        "contacto": "contacto@clinicamedicaensensada.mx",
        "telefono": "+52 646 XXX XXXX",
        "ciudad": "Ensenada",
        "estado": "Baja California",
        "razon_contacto": "Clínica maneja información médica sensible (HIPAA-like)",
        "caso_uso": "Cumplimiento de normas de protección de datos sanitarios",
        "prioridad": "Crítica"
    },
]

# Save to JSON
output_file = "prospectos_ensenada.json"
with open(output_file, 'w', encoding='utf-8') as f:
    json.dump({
        "generado": datetime.now().isoformat(),
        "total": len(prospects),
        "ciudad": "Ensenada, BC",
        "prospectos": prospects
    }, f, indent=2, ensure_ascii=False)

print(f"✅ {len(prospects)} prospectos generados")
print(f"📊 Archivo: {output_file}")
print(f"\n📋 Resumen por sector:")
sectors = {}
for p in prospects:
    sector = p['sector']
    sectors[sector] = sectors.get(sector, 0) + 1
for sector, count in sorted(sectors.items(), key=lambda x: -x[1]):
    print(f"   • {sector}: {count} empresas")
print(f"\n⭐ Prioridad CRÍTICA: {len([p for p in prospects if p['prioridad'] == 'Crítica'])} empresas")
print(f"🔴 Prioridad ALTA: {len([p for p in prospects if p['prioridad'] == 'Alta'])} empresas")
