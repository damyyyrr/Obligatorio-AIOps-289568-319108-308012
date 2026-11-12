# language: es
@live
Característica: Acceso y consulta de medicamentos de PharmaGo
  Los usuarios reciben resultados visibles al operar la aplicación real.
  La suite usa el gateway y SQL del entorno de laboratorio, sin simular respuestas.

  Escenario: Un administrador ingresa con credenciales válidas
    Dado que estoy en la pantalla de acceso
    Cuando ingreso las credenciales válidas del administrador de prueba
    Entonces accedo al panel de administrador con una sesión válida

  Escenario: Una contraseña incorrecta no permite iniciar sesión
    Dado que estoy en la pantalla de acceso
    Cuando ingreso una contraseña incorrecta para el administrador de prueba
    Entonces veo el error de contraseña y permanezco sin sesión
    Y puedo volver a intentar el acceso sin recargar la página

  Escenario: El catálogo permite abrir el detalle de un medicamento
    Dado que consulto el catálogo de medicamentos
    Entonces veo el medicamento de demostración con su farmacia y precio
    Cuando abro el detalle de ese medicamento
    Entonces veo su código, presentación y síntomas

  Escenario: Un medicamento inexistente muestra un error recuperable
    Cuando consulto el detalle de un medicamento inexistente
    Entonces veo un error y ningún detalle de medicamento
    Cuando regreso al catálogo desde la cabecera
    Entonces veo el medicamento de demostración con su farmacia y precio
