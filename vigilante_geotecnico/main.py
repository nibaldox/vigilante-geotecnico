"""Punto de entrada principal para el paquete vigilante_geotecnico."""

from vigilante_geotecnico.cli import parse_args
from vigilante_geotecnico.simulation import run_simulation


def main() -> None:
    """Función principal que orquesta la simulación geotécnica.

    Parsea argumentos de línea de comandos y ejecuta la simulación con los parámetros especificados.
    """
    args = parse_args()

    run_simulation(
        csv_path=args.csv,
        resample_rule=args.resample,
        step_points=args.step_points,
        lookback_min=args.lookback_min,
        accum_rate_hours=float(args.accum_rate_hours),
        accum_window_threshold_mm=float(args.accum_window_threshold_mm),
        baseline_fraction=args.baseline_fraction,
        sleep_seconds=args.sleep,
        llm_every=max(1, args.llm_every),
        dry_run=bool(args.dry_run),
        base_url=args.base_url,
        model=args.model,
        log_jsonl=args.log_jsonl,
        only_disagreements=bool(args.only_disagreements),
        start_at=args.start_at,
        v_alert=float(args.v_alert),
        v_alarm=float(args.v_alarm),
        d_alert=float(args.d_alert),
        v_alarm_with_d1=float(args.v_alarm_with_d1),
        v_alarm_with_d2=float(args.v_alarm_with_d2),
        summary_json=(args.summary_json or None),
        summary_top_k=int(args.summary_top_k),
        emit_every_min=args.emit_every_min,
        just_length=int(args.just_length),
    )


if __name__ == "__main__":
    main()
