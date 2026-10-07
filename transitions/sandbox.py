"""
transitions/sandbox.py - Run the transition sector alone and watch its decisions.

    python -m transitions.sandbox [--seconds 120] [--interval 8] [--bpm 120] [--seed 1]

Feeds scripted fake music into the front door at 30 fps, accepts every order, and prints
each transition: when it fired, why, which technique, and which mode each segment got.
No audio, no hardware, no project code.
"""
import argparse
import random
from typing import Callable, List, Optional

from transitions.api import OrderAck, TransitionOrders, create_transition_service
from transitions.fakes import fake_installation, fake_music

FPS = 30.0


def run(
    seconds: float = 120.0,
    interval: float = 8.0,
    bpm: float = 120.0,
    seed: Optional[int] = 1,
    echo: Optional[Callable[[str], None]] = print,
) -> List[TransitionOrders]:
    """Simulate `seconds` of music and return every set of orders the sector produced."""
    if seed is not None:
        random.seed(seed)
    service = create_transition_service({"auto_transition_time": interval})
    service.set_installation(fake_installation())

    fired: List[TransitionOrders] = []
    dt = 1.0 / FPS
    t = 0.0
    while t < seconds:
        music = fake_music(t, bpm)
        orders = service.update(dt, music)
        if orders is not None:
            fired.append(orders)
            if echo:
                techniques = sorted({o.technique for o in orders.orders})
                echo(f"[{t:6.1f}s] {music.scene:<11} energy={music.energy:.2f} "
                     f"reason={orders.reason:<12} technique={','.join(techniques)} "
                     f"duration={orders.orders[0].duration:.1f}s")
                for o in orders.orders:
                    echo(f"           {o.segment:<12} -> {o.target_mode}")
            service.acknowledge(OrderAck(accepted=tuple(o.segment for o in orders.orders)))
        t += dt
    if echo:
        echo(f"{len(fired)} transitions in {seconds:.0f}s")
    return fired


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the transition sector with fake music.")
    parser.add_argument("--seconds", type=float, default=120.0)
    parser.add_argument("--interval", type=float, default=8.0, help="auto transition interval (s)")
    parser.add_argument("--bpm", type=float, default=120.0)
    parser.add_argument("--seed", type=int, default=1)
    args = parser.parse_args()
    run(args.seconds, args.interval, args.bpm, args.seed)


if __name__ == "__main__":
    main()
