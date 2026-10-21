# Q-learning minimo con skrl

Este ejemplo entrena un agente para llegar a la meta en `FrozenLake-v1` (tablero de 4 x 4). Usa Q-learning tabular de skrl con PyTorch: no hay red neuronal ni GPU necesaria. El lago no resbala (`is_slippery=False`) para que la relacion entre accion y resultado sea facil de observar.

Para situar Q-learning frente a SARSA, DQN, PPO y otras familias, consulta [la clasificacion de RL](CLASIFICACION_RL.md).

## Preparacion (Linux/macOS)

Se recomienda Python 3.10 o superior. En la carpeta del proyecto:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

En VS Code, selecciona el interprete de `.venv` para ejecutar el ejemplo. La instalacion de PyTorch puede descargar varios cientos de MB; estas dependencias usan la instalacion estandar de pip (CPU o GPU segun plataforma y ruedas disponibles).

## Ejecutar

```bash
python frozen_lake.py
```

Para una prueba rapida de funcionamiento, sin esperar que haya aprendido una buena politica:

```bash
python frozen_lake.py --timesteps 32
```

El script imprime la tabla Q al acabar. Cada fila es una de las 16 casillas y cada columna una accion: izquierda (0), abajo (1), derecha (2), arriba (3). Un numero mayor indica una accion que el agente estima mejor en esa casilla. Despues intenta un episodio sin exploracion e indica si alcanzo la meta. Los resultados pueden variar entre ejecuciones. skrl tambien crea registros del entrenamiento en `runs/`.

## Como funciona

1. `gym.make` crea el entorno; `wrap_env` adapta sus observaciones y acciones a tensores para skrl.
2. `EpsilonGreedyPolicy` guarda `Q[casilla, accion]` en una tabla. En cada paso escoge la accion mejor valorada o, con probabilidad 0.1, una al azar para explorar. Los valores iniciales son 1 para animar a probar rutas aun no exploradas.
3. `Q_LEARNING` actualiza la tabla tras cada transicion observada, usando recompensa, siguiente casilla, tasa de aprendizaje 0.1 y descuento 0.99. No necesita memoria separada.
4. `SequentialTrainer` ejecuta el bucle de interaccion y entrenamiento durante `--timesteps` pasos (20 000 por defecto). Un episodio acaba cuando se llega a la meta, se cae en un agujero o se agota el limite de pasos; entonces comienza otro.

En FrozenLake solo se recibe recompensa 1 al llegar a la meta y 0 en los demas casos. La tabla es una estimacion, no una garantia de que el agente llegue siempre a la meta. La configuracion es deliberadamente pequena para mostrar las piezas de skrl; para otros entornos se necesitan espacios discretos para este agente tabular.

Documentacion: [Q-learning](https://skrl.readthedocs.io/en/latest/api/agents/q_learning.html), [modelos tabulares](https://skrl.readthedocs.io/en/latest/api/models/tabular.html) y [FrozenLake](https://gymnasium.farama.org/environments/toy_text/frozen_lake/).