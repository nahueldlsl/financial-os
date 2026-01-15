# 📈 Financial OS

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Docker](https://img.shields.io/badge/docker-%230db7ed.svg?style=flat&logo=docker&logoColor=white)
![React](https://img.shields.io/badge/react-%2320232a.svg?style=flat&logo=react&logoColor=%2361DAFB)
![FastAPI](https://img.shields.io/badge/FastAPI-005571?style=flat&logo=fastapi)
![PostgreSQL](https://img.shields.io/badge/postgres-%23316192.svg?style=flat&logo=postgresql&logoColor=white)

**Financial OS** es un sistema integral de gestión de finanzas personales e inversiones. Permite rastrear tu patrimonio neto, gestionar tu portafolio de acciones con precios en tiempo real (con caché inteligente), controlar tus flujos de caja (ingresos/gastos) y configurar las comisiones de tu broker.

Todo empaquetado en una arquitectura moderna, escalable y totalmente dockerizada.

---

## ⚡ Características Principales

- **📊 Dashboard en Tiempo Real:** Visualización clara de tu Patrimonio Neto (Net Worth), distribución de activos y rendimiento histórico.
- **🚀 Gestión de Portafolio:** Compra y venta de acciones con actualización automática de saldos y cálculo de precio promedio ponderado.
- **💰 Flujo de Caja:** Registro de ingresos y gastos personales que impactan directamente en tu liquidez.
- **⚙️ Comisiones Configurables:** Define las tarifas de tu broker (por acción entera o fracción) y edítalas manualmente en cada operación (ideal para DRIP).
- **⚡ Rendimiento Optimizado:** Sistema de caché de 15 minutos para cotizaciones bursátiles (Yahoo Finance) para minimizar latencia y consumo de API.
- **🐳 Docker Ready:** Despliegue en un solo comando.

---

## 🛠️ Tech Stack

- **Backend:** Python 3.10+, FastAPI, SQLModel (ORM), Pydantic.
- **Frontend:** React, TypeScript, Vite, TailwindCSS, Lucide Icons.
- **Base de Datos:** PostgreSQL (Compatible con Neon.tech, AWS RDS, o Local).
- **Infraestructura:** Docker & Docker Compose.

---

## 🚀 Guía de Inicio Rápido

Sigue estos pasos para ejecutar la aplicación en tu máquina local usando tu propia base de datos.

### Prerrequisitos

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) instalado y corriendo.
- [Git](https://git-scm.com/) instalado.

### 1. Clonar el Repositorio

```bash
git clone [https://github.com/TU_USUARIO/financial-os.git](https://github.com/TU_USUARIO/financial-os.git)
cd financial-os
