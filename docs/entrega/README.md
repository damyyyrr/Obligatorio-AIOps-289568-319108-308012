# Informe final del obligatorio AIOps

Informe con corte de código en `a1b2d56e20afec0797ceafd6f0a10b795fa72121`, merge del PR 44 en `obligatorio`. Las mediciones conservan los commits, imágenes y fechas de sus evidencias originales.

- [PDF de 10 páginas](Informe_Final_AIOps.pdf), incluida carátula e índice.
- [Word editable](Informe_Final_AIOps.docx).
- [Contenido en Markdown](informe-final.md).
- [Verificación documental](validacion-informe.json).

Incluye los nombres/legajos y docente confirmados por el usuario, las ocho secciones de la rúbrica, diagrama del laboratorio local, resultados reales, reflexión sobre prácticas comprobables y declaración de IA. Registra las decisiones del equipo sobre laboratorio local, recambio de tres servicios, dataset docente, tres integrantes y carga acotada de almacenamiento, conservando los límites de las mediciones. No declara realizada la defensa ni presentada la entrega en Gestión.

## Fuentes y reproducción

El contenido estructurado está en [fuentes/informe.json](fuentes/informe.json). [build_report.py](fuentes/build_report.py) genera el DOCX, Markdown y diagrama; requiere Python con `python-docx` y Pillow, y fuentes Arial de Windows. Se utilizó el runtime documental provisto por Codex.

Después de generar, renderizar con `render_docx.py` de la skill documental y LibreOffice, conservando el PDF mediante `--emit_pdf`. La exportación LibreOffice 7 de este equipo retuvo el índice pero omitió enlaces externos; [link_pdf.py](fuentes/link_pdf.py) los reconstruye desde las posiciones del texto y exige que coincidan con los vínculos del DOCX. Requiere `pypdf` y `pdfplumber`. Revisar todas las páginas y volver a verificar contenido, enlaces y límite de 10 páginas después de cualquier modificación.

La generación no inicia Docker/Kubernetes ni repite los ensayos. La revisión del equipo sobre contenido y decisiones sigue siendo necesaria antes de entregar. Los intermediarios de render y QA permanecen en `.runtime/informe-final`, fuera del paquete del informe.
