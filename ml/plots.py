"""Figuras estáticas para el informe, sin servidor ni ventanas interactivas."""
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np

from detectors import MODEL_COLUMNS


def make_plots(data, predictions, metrics, models, output):
    output = Path(output)
    colors = ("#185A81", "#A84913")
    with plt.rc_context({"font.size": 10, "axes.spines.top": False, "axes.spines.right": False}):
        fig, axes = plt.subplots(2, 1, figsize=(11, 6.4), sharex=True, layout="constrained")
        for ax, ((name, key), color) in zip(axes, zip(MODEL_COLUMNS.items(), colors)):
            score, flag = predictions[f"score_{key}"], predictions[f"flag_{key}"]
            ax.plot(data.timestamp, score, color=color, lw=1.2, label="Score de anomalía")
            ax.scatter(data.loc[flag, "timestamp"], score[flag], color="#BA2424", s=23, label="Ventana alertada", zorder=3)
            threshold = -models.forest.offset_ if key == "if" else 0
            ax.axhline(threshold, color="#4F5964", ls="--", lw=1, label="Umbral del detector")
            ax.set(title=name, ylabel="Score (escala propia)")
            ax.grid(alpha=0.2)
            ax.legend(loc="upper left", fontsize=8, ncol=3)
        axes[-1].xaxis.set_major_formatter(mdates.DateFormatter("%H:%M"))
        axes[-1].set_xlabel("Hora sintética del 03/06/2026 (sin zona horaria)")
        fig.suptitle("Scores y alertas: 300 ventanas evaluadas sobre la muestra de entrenamiento")
        fig.savefig(output / "scores_timeline.png", dpi=150)
        plt.close(fig)

        fig, axes = plt.subplots(1, 2, figsize=(11, 4.5), sharex=True, sharey=True, layout="constrained")
        truth = data.is_anomaly.to_numpy(dtype=bool)
        for ax, (name, key) in zip(axes, MODEL_COLUMNS.items()):
            flags = predictions[f"flag_{key}"].to_numpy(dtype=bool)
            groups = ((~truth & ~flags, "Normal no alertado (TN)", "#87939D", "o", 15),
                      (truth & flags, "Incidente alertado (TP)", "#197C58", "o", 35),
                      (~truth & flags, "Falso positivo (FP)", "#D58911", "^", 48),
                      (truth & ~flags, "Falso negativo (FN)", "#BC3030", "x", 36))
            for mask, label, color, marker, size in groups:
                ax.scatter(data.loc[mask, "requests"], 100 * data.loc[mask, "error_rate"],
                           label=label, c=color, marker=marker, s=size, alpha=0.75)
            ax.set(title=name, xlabel="Requests / minuto")
            ax.grid(alpha=0.15)
        axes[0].set_ylabel("Error rate (%)")
        handles, labels = axes[0].get_legend_handles_labels()
        fig.legend(handles, labels, fontsize=8, loc="outside lower center", ncol=4)
        fig.suptitle("Proyección de dos variables: el entrenamiento utiliza cuatro")
        fig.savefig(output / "projection.png", dpi=150)
        plt.close(fig)

        fig, axes = plt.subplots(1, 3, figsize=(12, 3.8), layout="constrained")
        names = list(MODEL_COLUMNS)
        positions = np.arange(3)
        for i, row in metrics.iterrows():
            values = row[["precision", "recall", "f1"]].to_numpy(dtype=float)
            axes[0].bar(positions + (i - 0.5) * 0.36, values, width=0.36, color=colors[i], label=names[i])
        axes[0].set(xticks=positions, xticklabels=["Precisión", "Recall", "F1"], ylim=(0, 1.05), title="Métricas por ventana")
        axes[0].legend(fontsize=7, loc="upper right")
        for ax, (_, row) in zip(axes[1:], metrics.iterrows()):
            matrix = np.array([[row.tn, row.fp], [row.fn, row.tp]], dtype=int)
            ax.imshow(matrix, cmap="Blues", vmin=0, vmax=int(metrics.tn.max()))
            for (r, c), value in np.ndenumerate(matrix):
                ax.text(c, r, str(value), ha="center", va="center", color="white" if value > metrics.tn.max() / 2 else "#18232A", fontsize=13)
            ax.set(xticks=[0, 1], xticklabels=["Normal", "Alerta"], yticks=[0, 1],
                   yticklabels=["Normal", "Anomalía"], xlabel="Predicción", ylabel="Etiqueta de evaluación",
                   title=row.model.replace(" RBF", ""))
        fig.suptitle("Comparación descriptiva; sin conjunto de prueba independiente")
        fig.savefig(output / "comparison.png", dpi=150)
        plt.close(fig)
