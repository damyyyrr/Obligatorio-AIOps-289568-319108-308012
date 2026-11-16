# Informe final del obligatorio AIOps

Informe con corte documental en `bb89cdc5e369c236465ea62be7167ff7f7d96943`, que incorpora las evidencias físicas y la matriz actualizada. Las corridas en tres PCs registran código `ae24ebe`; cada medición conserva el commit, las imágenes y el entorno de su evidencia original.

- [PDF de 10 páginas](Informe_Final_AIOps.pdf), incluida carátula e índice.
- [Word editable](Informe_Final_AIOps.docx).
- [Contenido en Markdown](informe-final.md).
- [Verificación documental](validacion-informe.json).

Incluye los nombres/legajos y docente confirmados por el usuario, las ocho secciones de la rúbrica, el diagrama del despliegue físico, resultados reales, reflexión sobre prácticas comprobables y declaración de IA. Distingue los seis casos de caos aprobados en tres PCs del rollout/rollback y la validación detallada de telemetría realizados localmente. Conserva el FAIL del primer intento de red, los límites de RAM/almacenamiento y la falta de medición de reconocimiento humano. No declara realizada la defensa ni presentada la entrega en Gestión.

La figura 1 de la página 2 muestra Gateway en PC A, Users en PC B y Pharmacy en PC C, con k3s en WSL2 y Tailscale. Se utiliza el diagrama publicado con las evidencias físicas. Los laboratorios Minikube previos conservan sus propios diagramas y resultados. La actualización documental no ejecuta nuevas pruebas ni modifica infraestructura.

## Fuentes y reproducción

El contenido estructurado está en [fuentes/informe.json](fuentes/informe.json). [build_report.py](fuentes/build_report.py) genera el DOCX, Markdown y diagrama; requiere Python con `python-docx` y Pillow, y fuentes Arial de Windows. Se utilizó el runtime documental provisto por Codex.

Después de generar, exportar el DOCX a PDF con Microsoft Word o con el motor de documentos disponible. En esta revisión se usó Word de Windows en una instancia oculta y el pipeline PNG de `render_docx.py` para revisar todas las páginas. Comprobar contenido, enlaces e índice con [verify_report.py](fuentes/verify_report.py); requiere `pypdf` y `python-docx`. También contrasta las siete corridas comprimidas, la distribución de pods y las cifras originales, sin iniciar infraestructura.

Si el exportador omite enlaces externos, [link_pdf.py](fuentes/link_pdf.py) permite reconstruirlos desde las posiciones del texto y exige paridad con el DOCX; requiere `pypdf` y `pdfplumber`. Se utilizó con la exportación anterior de LibreOffice 7; no debe aplicarse a un PDF que ya conserva esos enlaces. Revisar todas las páginas y el límite de 10 páginas después de cualquier modificación.

La generación no inicia Docker/Kubernetes ni repite los ensayos. La revisión del equipo sobre contenido y decisiones sigue siendo necesaria antes de entregar. Los intermediarios de render y QA permanecen en `.runtime/informe-final`, fuera del paquete del informe.
