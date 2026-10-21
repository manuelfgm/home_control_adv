# Dónde encaja Q-learning en aprendizaje por refuerzo

En aprendizaje por refuerzo (RL), un agente observa un estado, elige una accion y recibe una recompensa del entorno. Su objetivo es aprender una **politica** (regla para elegir acciones) que maximice la recompensa acumulada. A diferencia del aprendizaje supervisado, no recibe una etiqueta con la accion correcta en cada estado.

No hay un unico arbol de algoritmos: las clasificaciones siguientes son **ejes independientes**. Por ejemplo, Q-learning puede ser a la vez *sin modelo*, *basado en valor*, *off-policy* y *tabular*.

## 1. ¿Se aprende un modelo del entorno?

| Familia | Que aprende o utiliza | Ventaja | Limitacion / ejemplo |
| --- | --- | --- | --- |
| **Basada en modelo** (*model-based*) | Una descripcion de como cambian los estados y que recompensa producen las acciones; puede conocerse de antemano o aprenderse. Con ella planifica antes de actuar. | Puede aprovechar mejor cada experiencia real. | Un modelo incorrecto induce malas decisiones; por ejemplo, planificacion con un simulador aprendido. |
| **Sin modelo** (*model-free*) | Valores o una politica directamente, sin predecir las transiciones para planificar. | Evita construir un modelo del entorno. | Puede necesitar mas interacciones; **Q-learning**, SARSA y PPO son ejemplos. |

**Q-learning** es *model-free*: actualiza estimaciones a partir de lo que observa, sin aprender las reglas del lago. Que Gymnasium conozca internamente esas reglas no significa que el agente las use.

## 2. ¿Que se aprende para decidir?

| Familia | Idea | Ejemplos | Cuando resulta util |
| --- | --- | --- | --- |
| **Basada en valor** | Estima $V(s)$ (calidad de un estado) o $Q(s,a)$ (calidad de una accion en un estado); elige una accion con alto valor. | Q-learning, SARSA, DQN. | Acciones discretas; es sencillo comparar las opciones posibles. |
| **Basada en politica** (*policy gradient*) | Ajusta directamente una politica $\pi(a\mid s)$ que asigna probabilidades o acciones a cada observacion. | REINFORCE, PPO. | Acciones continuas o politicas estocasticas; puede ser mas costosa en muestras. |
| **Actor-critic** | Un *actor* aprende la politica y un *critic* estima el valor para guiar su mejora. | A2C, SAC, DDPG, TD3; PPO suele usar un critic. | Combina una politica flexible con una señal de aprendizaje basada en valor. |

La politica del ejemplo elige la accion con mayor $Q(s,a)$ casi siempre. La exploracion $\epsilon$-greedy introduce acciones aleatorias para descubrir caminos nuevos. El valor $Q$ es una prediccion de recompensa futura, no la recompensa inmediata de esa casilla.

## 3. ¿De que politica proceden los datos de entrenamiento?

| Familia | Regla | Ejemplos | Consecuencia |
| --- | --- | --- | --- |
| **On-policy** | Aprende sobre la politica que esta generando los datos (incluida su exploracion). | SARSA, PPO, A2C. | Los datos viejos dejan de representar bien a la politica actual; se reutilizan menos. |
| **Off-policy** | Puede aprender sobre una politica objetivo distinta de la que produjo los datos. | Q-learning, DQN, SAC, TD3. | Permite aprender de acciones exploratorias y, en muchos algoritmos, reutilizar experiencias guardadas. |

Q-learning es *off-policy* porque toma acciones con exploracion, pero actualiza $Q(s,a)$ usando la **mejor** accion estimada en el siguiente estado, aunque no sea la que realmente tomaria al explorar. SARSA, la alternativa tabular cercana, usa la **siguiente accion realmente elegida** y por eso es *on-policy*. *Off-policy* no implica necesariamente una memoria de experiencias: el ejemplo actualiza la tabla paso a paso y no usa un *replay buffer*.

## 4. ¿Como se representan los valores o la politica?

| Representacion | Idea | Ejemplo | Limite |
| --- | --- | --- | --- |
| **Tabular** | Una entrada por cada par estado-accion. | Q-learning en FrozenLake: 16 estados x 4 acciones. | No escala bien a estados continuos o imagenes. |
| **Aproximacion con redes** (*deep RL*) | Una red predice valores o acciones a partir de observaciones. | DQN aproxima $Q(s,a)$; PPO aproxima politica y valor. | Mas parametros y ajustes; requiere entrenamiento de la red. |

Q-learning es un algoritmo, no sinonimo de "tabla": hay variantes con aproximadores. **DQN** es una alternativa para observaciones grandes: aprende valores Q con una red, normalmente usando una memoria de experiencias y una red objetivo. Este ejemplo tabular usa PyTorch como soporte de skrl, pero **no** entrena una red neuronal.

## 5. ¿Cuando se actualiza con la recompensa futura?

| Enfoque | Como estima el futuro | Ejemplos |
| --- | --- | --- |
| **Monte Carlo** | Espera hasta el final del episodio y usa el retorno observado. | REINFORCE; evaluacion Monte Carlo. |
| **Diferencia temporal (TD)** | Actualiza antes de terminar, usando una estimacion del siguiente estado (*bootstrap*). | Q-learning, SARSA, DQN, A2C. |
| **Mixto** | Combina varias longitudes de retorno. | PPO suele usar GAE para estimar ventajas. |

La actualizacion de Q-learning es:

$$
Q(s,a) \leftarrow Q(s,a) + \alpha\left[r + \gamma(1-d)\max_{a'}Q(s',a') - Q(s,a)\right]
$$

Aqui $r$ es la recompensa observada, $\alpha$ la tasa de aprendizaje, $\gamma$ el descuento del futuro y $d=1$ si el episodio termino. El maximo sobre $a'$ explica por que aprende la politica *greedy* aunque explore con otras acciones. En el ejemplo, $\alpha=0.1$ y $\gamma=0.99$.

## Elegir una alternativa

| Si tienes... | Primer candidato | Motivo |
| --- | --- | --- |
| Pocos estados y acciones discretas | **Q-learning tabular** | Ves la tabla completa y entiendes cada actualizacion. |
| Pocos estados, pero quieres aprender el valor de la propia politica exploratoria | **SARSA** | Cambia la regla del siguiente valor; compara el efecto de explorar. |
| Observaciones grandes y acciones discretas | **DQN** | Sustituye la tabla por una red. |
| Acciones continuas o quieres una politica estocastica | **PPO** | Aprende la politica directamente con ayuda de un critic; es on-policy. |
| Acciones continuas y quieres reutilizar datos | **SAC** o **TD3** | Son actor-critic off-policy; requieren mas componentes y ajuste. |
| Un simulador fiable o transiciones conocidas | **Planificacion basada en modelo** | Permite probar decisiones sin gastar tantas interacciones reales. |

Estas son guias, no reglas absolutas: la estabilidad, el coste de recopilar experiencias y la calidad de las observaciones tambien importan. Para seguir el ejemplo practico, vuelve a [README.md](README.md) y [frozen_lake.py](frozen_lake.py).

Referencia: [algoritmos y agentes de skrl](https://skrl.readthedocs.io/en/latest/api/agents.html).