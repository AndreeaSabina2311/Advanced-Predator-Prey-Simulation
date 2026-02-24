# Advanced-Predator-Prey-Simulation


### Requirements:

#### Reproduction Mechanism:
- Implement reproduction for prey when certain conditions are met (e.g. high-energy prey will periodically seek each other out - when they meet they stop for a few timesteps and then a 3rd prey agent gets born).
- Implement similar reproduction for predators.

#### Energy Levels:
- Introduce energy levels for both predators and prey.
- Prey lose energy over time and gain energy by eating food resources.
- Predators lose energy over time and gain energy by consuming prey.
- Agents die when their energy reaches zero.

#### Food Resources:
- Add food resources that prey can consume to gain energy.
- Prey is interested in food only when energy is below a certain threshold.
- Visualize food resources on the screen.

#### Improved AI Behaviors:
- Enhance prey behaviors to include flocking (similar to boids).
- Slightly increase speed of agents based on flock size.

#### Obstacle Avoidance:
- Introduce obstacles in the environment that agents must navigate around.

#### History Tracking:
- Save the history of the environment throughout timesteps.
- Include graphs showing:
  - population changes over time
  - birth rates of prey and predators

#### User Interaction:
- Provide any 3 interactible controls to adjust simulation in real time (e.g., reproduction rate, energy consumption, toggling flocking behavior, manually adding food, manually adding agents, manually adding obstacles, etc.).

Play around with your simulation and simulation parameters until you can reach a relatively stable environment state. A state in which both predators and prey cohabit without any or both of the species dying out completely.



### (Optional) Implement both options for extra points.
