# Corrección de aislamiento de prueba .NET — 14/11/2026

**Resultado nuevo: 319/319 pruebas aprobadas**, sin fallos ni omisiones: 298 de `PharmaGo.Test` y 21 de `PharmaGo.ApiGateway.Test`. El [resumen extraído de los dos TRX](summary.json) conserva conteos, marcas temporales con offset, SDK y hashes de los originales locales.

## Código verificado

El [PR #42](https://github.com/damyyyrr/Obligatorio-AIOps-289568-319108-308012/pull/42), commit `6c68a9cdbb251b7b78b5afddd6f5afce64e615bd`, modifica solo [PurchasesDetailRepositoryTest.cs](../../../Implementacion%20K8S/Codigo/Backend/PharnaGo.Test/DataAccess.Test/PurchasesDetailRepositoryTest.cs):

- Base InMemory con nombre único en cada `TestInitialize` y eliminación de esa base aislada en cleanup.
- Dos detalles insertados; consulta por el ID generado del detalle esperado, desde un contexto nuevo.
- Comprobación de ID y cantidad del resultado, además de no nulo.

Se verificó que el archivo ejecutado coincide con el blob del commit base `2f125b89bf5c8c34a8748367b068bbdb8cd17975`, que integra el PR #42. No había diferencias en `Backend/`. El árbol tenía cambios documentales: `workingTreeDirty=true` se conserva en el resumen, sin presentarlo como un commit limpio.

La falla previa estaba documentada en [#8](../issue-8-20261111/README.md): base compartida `PharmaGoDb` y consulta por `Id == 1`. Sus 290/291 se conservan como resultado histórico; la suite actual tiene 319 pruebas.

## Ejecución y reproducción

Desde la raíz del repositorio, con SDK .NET y dependencias restauradas:

```powershell
dotnet test 'Implementacion K8S/Codigo/Backend/PharmaGo.sln' --no-restore --nologo --verbosity quiet --results-directory '.runtime/docs-status-20261114/dotnet' --logger 'trx;LogFilePrefix=status'
```

Se usó SDK `10.0.203` y destino `net6.0`. Los TRX originales quedan en `.runtime/docs-status-20261114/dotnet`; el resumen versionado publica solo contadores, tiempos y metadatos. No se publican los TRX completos ni logs de compilación con rutas locales. Se mantienen advertencias previas de dependencias y nulabilidad; el resultado no se describe como compilación sin advertencias.

Esta ejecución verifica la suite .NET local. No inició Docker, Kubernetes, navegador ni escenarios de caos y no mide disponibilidad del despliegue.
