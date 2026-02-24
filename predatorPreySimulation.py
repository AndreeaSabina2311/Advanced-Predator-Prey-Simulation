import pygame
import random
import math
import matplotlib.pyplot as plt
import pandas as pd

# Initialize Pygame
pygame.init()

# Screen dimensions
WIDTH, HEIGHT = 800, 600

# Colors
BACKGROUND_COLOR = (30, 30, 30)
PREY_COLOR = (0, 255, 0)
PREDATOR_COLOR = (255, 0, 0)
FOOD_COLOR = (100, 200, 255)
OBSTACLE_COLOR = (150, 150, 150) # NOU: Culoare pentru obstacole (Gri)
TEXT_COLOR = (200, 200, 200)

# Sex marker colors
MALE_MARKER_COLOR = (0, 0, 255)
FEMALE_MARKER_COLOR = (255, 100, 200)

# Culoare pentru raza de Flocking (semi-transparentă)
# RGB și al patrulea element este valoarea Alpha (0-255)
FLOCKING_CIRCLE_COLOR = (50, 150, 50, 50) # Culoare verde semi-transparent

# Flocking constants
# Raza în care prada caută alți agenți Prey pentru a forma stol
FLOCKING_RADIUS = 30 
# Raza minimă la care prada se îndepărtează de alți agenți Prey (evitare coliziuni)
SEPARATION_RADIUS = 15 

# Forțele de ajustare (cu cât e mai mare, cu atât e mai puternic efectul)
COHESION_WEIGHT = 0.01
ALIGNMENT_WEIGHT = 0.05
SEPARATION_WEIGHT = 0.05
WANDER_WEIGHT = 0.005

# Frame rate
FPS = 60

# Initialize screen and clock
# MODIFICARE AICI: Adaugă flag-ul SRCALPHA pentru a permite transparența
screen = pygame.display.set_mode((WIDTH, HEIGHT), pygame.SRCALPHA)
pygame.display.set_caption("Predator-Prey Simulation")
clock = pygame.time.Clock()

# Font for text
FONT = pygame.font.SysFont(None, 24)

# ==============================================================================
# CLASA NOUĂ: OBSTACLE
# ==============================================================================
class Obstacle:
    """Class representing a static obstacle."""
    # Constructor pentru Obstacle
    def __init__(self, position=None, radius=20):
        # Poziție random (excluzând marginile) dacă nu e specificată
        self.position = position or pygame.math.Vector2(random.uniform(50, WIDTH - 50), random.uniform(50, HEIGHT - 50))
        self.radius = radius
        self.color = OBSTACLE_COLOR # Culoare gri

    def draw(self):
        """Draw the obstacle as a solid circle."""
        pygame.draw.circle(screen, self.color, (int(self.position.x), int(self.position.y)), self.radius)

# ==============================================================================
# CLASA AGENT (MODIFICARE: _obstacle_avoidance, NOU: _resolve_obstacle_collision)
# ==============================================================================
class Agent:
    """Base class for all agents in the simulation."""
    def __init__(self, position=None, velocity=None, speed=2, color=PREY_COLOR, max_energy=100, sex=None, mating_duration_sec=2):
        self.position = position or pygame.math.Vector2(random.uniform(0, WIDTH), random.uniform(0, HEIGHT))
        # Ensure non-zero velocity
        vel = velocity or pygame.math.Vector2(random.uniform(-1, 1), random.uniform(-1, 1))
        if vel.length_squared() == 0:
            vel = pygame.math.Vector2(1, 0)
        self.velocity = vel.normalize()
        self.initial_base_speed = speed # Viteza de baza initiala
        self.base_speed = speed  # Viteza de bază (maximă) ajustabilă
        self.speed = speed
        self.color = color
        self.trail = []
        self.max_trail_length = 10
        self.max_energy = max_energy
        self.energy = max_energy
        
        # Sex: 'M' sau 'F' (dacă e None, se alege random 50-50)
        if sex is None:
            self.sex = 'F' if random.random() < 0.5 else 'M'
        else:
            self.sex = sex

        # Atribute pentru reproducere
        self.is_mating = False
        self.mating_timer = 0
        # MODIFICARE: Durata se bazează pe parametrul nou (suprascris în subclase)
        self.mating_duration = FPS * mating_duration_sec  # Durată în funcție de FPS
        self.mate_partner = None
        self.is_pregnant = False # Unul dintre parteneri devine "pregnant" și va naște
        self.reproduction_cooldown = 0
        self.just_started_mating = False  # Flag folosit de Simulation pentru a elibera pradatorii care le urmau
        self.ready_to_reproduce = False
        self.flock_size = 1 # Mărimea grupului (folosit pentru ajustarea vitezei)


    def update_position(self):
        """Update the agent's position based on its velocity and speed."""
        self.update_speed_based_on_energy()
        self.position += self.velocity * self.speed
        self._bounce_off_walls()
        self._update_trail()
        self.lose_energy()
        # NOTĂ: Coliziunea cu obstacolele va fi rezolvată în metodele update
        # ale claselor Prey și Predator, după apelarea update_position.


    def update_speed_based_on_energy(self):
        """Update speed based on current energy level."""
        energy_ratio = self.energy / self.max_energy
        # Speed scaling: minimum 50% speed, maximum 100% speed
        speed_multiplier = 0.5 + (0.5 * energy_ratio)
        # Viteza finală se bazează pe self.base_speed (care e ajustat de flocking)
        self.speed = self.base_speed * speed_multiplier

    def lose_energy(self):
        """Decrease energy over time."""
        # Consum de energie mai mic dacă agentul este în repaus pentru împerechere
        energy_loss = 0.1
        if self.is_mating:
            energy_loss = 0.05 

        self.energy -= energy_loss
        if self.energy < 0:
            self.energy = 0

    def is_alive(self):
        """Check if the agent is still alive."""
        return self.energy > 0

    def _bounce_off_walls(self):
        """Bounce the agent off the screen edges."""
        if self.position.x < 0 or self.position.x > WIDTH:
            self.velocity.x *= -1
        if self.position.y < 0 or self.position.y > HEIGHT:
            self.velocity.y *= -1

        # Keep position within bounds
        self.position.x = max(0, min(self.position.x, WIDTH))
        self.position.y = max(0, min(self.position.y, HEIGHT))

    def _update_trail(self):
        """Update the trail of the agent for visualization."""
        self.trail.append(self.position.copy())
        if len(self.trail) > self.max_trail_length:
            self.trail.pop(0)

    def draw_trail(self):
        """Draw the trail of the agent."""
        if len(self.trail) > 1:
            # Grosime de 2 pentru vizibilitate sporită
            pygame.draw.lines(screen, self.color, False, [(int(p.x), int(p.y)) for p in self.trail], 2)

    def draw(self):
        """Method to draw the agent. To be implemented by subclasses."""
        raise NotImplementedError("Draw method must be implemented by subclasses.")

    def draw_energy_bar(self):
        """Draw an energy bar above the agent."""
        bar_width = 20
        bar_height = 3
        bar_x = int(self.position.x - bar_width / 2)
        bar_y = int(self.position.y - 15)
        
        # Background bar (red)
        pygame.draw.rect(screen, (100, 0, 0), (bar_x, bar_y, bar_width, bar_height))
        
        # Energy bar (green)
        energy_width = int((self.energy / self.max_energy) * bar_width)
        pygame.draw.rect(screen, (0, 255, 0), (bar_x, bar_y, energy_width, bar_height))
    
    # MODIFICARE: Adăugare condiție energie minimă de 70%
    def is_energy_sufficient_for_mating(self):
        """Check if the agent has enough energy (>= 70% of max_energy) to start mating."""
        return self.energy >= self.max_energy * 0.7 

    # MODIFICARE: can_reproduce verifică acum și energia
    def can_reproduce(self):
        """Check if agent can reproduce."""
        # Se reproduce DOAR dacă este gata (fără cooldown) ȘI are energie suficientă
        return self.reproduction_cooldown == 0 and self.is_energy_sufficient_for_mating()
    
    # MODIFICARE: _find_potential_mate folosește noua can_reproduce()
    def _find_potential_mate(self, other_agents, mate_detection_radius):
        """Find a potential mate within detection radius."""
        for agent in other_agents:
            # Condiții: Să fie alt agent, să poată reproduce (inclusiv energie și cooldown), să nu fie deja în împerechere, și sex opus
            if (agent != self and 
                agent.can_reproduce() and 
                not agent.is_mating and 
                agent.sex != self.sex):
                distance = self.position.distance_to(agent.position)
                if distance < mate_detection_radius:
                    return agent
        return None

    def seek_mate(self, mate):
        """Move towards a potential mate."""
        distance = self.position.distance_to(mate.position)
        if distance < 8:  # Destul de aproape pentru împerechere
            self.start_mating(mate)
        else:
            # Dacă sunt foarte aproape, se îndreaptă unul spre celălalt
            direction = (mate.position - self.position)
            if direction.length_squared() != 0:
                self.velocity = direction.normalize()

    def start_mating(self, mate):
        """Start the mating process with a partner."""
        # Setează starea de împerechere pentru ambii parteneri
        self.is_mating = True
        self.mate_partner = mate
        self.mating_timer = 0
        self.velocity = pygame.math.Vector2(0, 0) # Se oprește
        
        mate.is_mating = True
        mate.mate_partner = self
        mate.mating_timer = 0
        mate.velocity = pygame.math.Vector2(0, 0) # Se oprește
        
        # Determinăm cine devine pregnant: femela devine pregnant
        if self.sex == 'F':
            self.is_pregnant = True
            mate.is_pregnant = False
        elif mate.sex == 'F':
            mate.is_pregnant = True
            self.is_pregnant = False
        else:
            # fallback (nu ar trebui să se întâmple deoarece cerem sex opus)
            self.is_pregnant = False
            mate.is_pregnant = False
        
        # Marcare pentru Simulation astfel încât prădătorii care îi urmăreau să se reorienteze
        self.just_started_mating = True
        mate.just_started_mating = True

    def finalize_mating(self):
        """Finalize the mating process and apply cooldown.
        
        Returnează True dacă acest agent a fost cel care a resetat (agentul pregnant) și poate naște, False altfel.
        """
        # Logica pentru agentul non-pregnant (se resetează, dar nu resetează partenerul)
        if not self.is_pregnant:
            self.is_mating = False
            self.reproduction_cooldown = FPS * 5
            self.mate_partner = None
            self.just_started_mating = False
            self.ready_to_reproduce = False
            return False

        # Logica pentru agentul pregnant (care este responsabil pentru naștere și resetare)
        self.is_mating = False
        self.reproduction_cooldown = FPS * 5 # Cooldown de 5 secunde
        # Fără pierdere de energie la reproducere

        if self.mate_partner:
            # Aplicăm aceleași efecte și partenerului și îl resetăm complet
            self.mate_partner.is_mating = False
            self.mate_partner.reproduction_cooldown = FPS * 5
            self.mate_partner.mate_partner = None
            self.mate_partner.is_pregnant = False
            self.mate_partner.just_started_mating = False
            self.mate_partner.ready_to_reproduce = False
        
        self.mate_partner = None
        self.is_pregnant = False
        self.just_started_mating = False
        self.ready_to_reproduce = False
        return True # Returnează True pentru a declanșa nașterea
    
    # NOU DIN CEREREA ANTERIOARĂ: Metoda de evitare a obstacolelor (comportament de steering)
    def _obstacle_avoidance(self, obstacles):
        """
        Calculates the steering force to avoid nearby obstacles.
        Returns a steering force vector.
        """
        # Raza de detecție pentru obstacole 
        avoidance_radius = 20 
        # Cât de departe să "vadă" agentul în fața lui
        lookahead = 30 
        
        lookahead_point = self.position + self.velocity * lookahead
        
        nearest_obstacle = None
        min_distance = float('inf')
        
        # 1. Detectează cel mai apropiat obstacol
        for obstacle in obstacles:
            distance = self.position.distance_to(obstacle.position)
            if distance < obstacle.radius + avoidance_radius:
                
                vector_to_obstacle = obstacle.position - self.position
                
                if self.velocity.length_squared() != 0:
                    projection_length = vector_to_obstacle.dot(self.velocity.normalize())
                else:
                    projection_length = 0 

                if projection_length > 0:
                    
                    closest_point_on_path = self.position + self.velocity.normalize() * projection_length
                    distance_from_path = obstacle.position.distance_to(closest_point_on_path)
                    
                    if distance_from_path < obstacle.radius + 5: # 5 e un buffer
                        if distance < min_distance:
                            min_distance = distance
                            nearest_obstacle = obstacle

        if nearest_obstacle:
            avoidance_vector = self.position - nearest_obstacle.position
            avoidance_vector = avoidance_vector.normalize() / max(min_distance, 0.1) 
            
            return avoidance_vector * 0.5 
            
        return pygame.math.Vector2(0, 0)
    
    # NOU: Metoda de rezolvare fizică a coliziunilor (pentru a garanta că NU TRECE)
    def _resolve_obstacle_collision(self, obstacles):
        """
        Physically resolves overlap between agent and obstacles, forcing the agent 
        out of the obstacle if penetration occurred during movement.
        """
        # Raza agentului Prey (4) sau o estimare pentru Predator (triunghi)
        AGENT_RADIUS = 5 
        
        for obstacle in obstacles:
            distance = self.position.distance_to(obstacle.position)
            min_distance = obstacle.radius + AGENT_RADIUS
            
            # Verifică penetrarea
            if distance < min_distance:
                # Calculează adâncimea de penetrare
                penetration_depth = min_distance - distance
                
                # Calculează direcția de împingere (vectorul de la obstacol la agent)
                if distance == 0:
                    # Direcție aleatorie dacă agenții sunt perfect suprapuși
                    push_direction = pygame.math.Vector2(random.uniform(-1, 1), random.uniform(-1, 1)).normalize()
                else:
                    push_direction = (self.position - obstacle.position).normalize()
                
                # Mută agentul în afara obstacolului (Forțare fizică)
                self.position += push_direction * penetration_depth
                
                # Opțional: Reducem viteza agentului pentru a simula impactul
                self.velocity *= 0.1 

# ==============================================================================
# CLASA PREY (MODIFICARE: update - apel rezoluție coliziune)
# ==============================================================================
class Prey(Agent):
    """Class representing a prey agent."""
    def __init__(self, sex=None):
        # MODIFICARE: Durata de împerechere setată la 3 secunde
        super().__init__(speed=2, color=PREY_COLOR, max_energy=100, sex=sex, mating_duration_sec=3)
        self.vision_radius = 50  # Detection radius for predators
        self.is_targeted = False  # Flag pentru a ști dacă este urmărită
        self.food_detection_radius = 30  # Detection radius for food
        self.mate_detection_radius = 60  # Raza de detectare pentru parteneri

    def can_reproduce(self):
        # Suprascrie doar pentru a folosi logica din baza (care include deja verificarea energiei)
        return super().can_reproduce()

    def update_speed_based_on_flock(self, num_neighbors):
        """Ajustează viteza de bază a prăzii în funcție de numărul de vecini (dimensiunea stolului)."""
        
        self.flock_size = num_neighbors + 1 
        
        speed_increase = min(self.flock_size / 10 * 0.5, 1.5)
        
        self.base_speed = self.initial_base_speed + speed_increase
        self.base_speed = max(self.base_speed, self.initial_base_speed)

    def _get_neighbors(self, other_prey):
        """Găsește vecinii apropiați (alți agenți Prey) în raza de Flocking."""
        neighbors = []
        for prey in other_prey:
            distance = self.position.distance_to(prey.position)
            if distance < FLOCKING_RADIUS:
                neighbors.append(prey)
        return neighbors

    def _cohesion(self, neighbors):
        """Regula 1: Se îndreaptă spre centrul de masă al stolului."""
        if not neighbors:
            return pygame.math.Vector2(0, 0)
        
        center_of_mass = pygame.math.Vector2(0, 0)
        for prey in neighbors:
            center_of_mass += prey.position
        
        center_of_mass /= len(neighbors)
        cohesion_vector = (center_of_mass - self.position).normalize()
        return cohesion_vector * COHESION_WEIGHT

    def _alignment(self, neighbors):
        """Regula 2: Încearcă să se alinieze cu viteza medie a vecinilor."""
        if not neighbors:
            return pygame.math.Vector2(0, 0)
        
        average_velocity = pygame.math.Vector2(0, 0)
        for prey in neighbors:
            average_velocity += prey.velocity
            
        average_velocity /= len(neighbors)
        alignment_vector = (average_velocity - self.velocity)
        return alignment_vector * ALIGNMENT_WEIGHT


    def _separation(self, neighbors):
        """Regula 3: Evită să se apropie prea mult de ceilalți agenți din stol (evită coliziunile)."""
        separation_vector = pygame.math.Vector2(0, 0)
        for prey in neighbors:
            distance = self.position.distance_to(prey.position)
            if 0 < distance < SEPARATION_RADIUS:
                # Vector de forță invers proporțională cu distanța
                diff = self.position - prey.position
                if diff.length_squared() != 0:
                    separation_vector += diff.normalize() / distance
                    
        return separation_vector * SEPARATION_WEIGHT
    
    def _apply_flocking_behavior(self, other_prey):
        """Aplică regulile Boids pentru a calcula noua direcție bazată pe vecini."""
        neighbors = self._get_neighbors(other_prey)
        
        self.update_speed_based_on_flock(len(neighbors))

        if not neighbors:
            return pygame.math.Vector2(0, 0) 
        
        cohesion = self._cohesion(neighbors)
        alignment = self._alignment(neighbors)
        separation = self._separation(neighbors)
        
        flocking_force = cohesion + alignment + separation
        
        self.velocity += flocking_force
        
        if self.velocity.length_squared() != 0:
            self.velocity = self.velocity.normalize()
        
        return flocking_force

    # MODIFICARE: Adaugă apelul self._resolve_obstacle_collision(obstacles)
    def update(self, predators, food_list, other_prey, obstacles):
        """Update the prey's state based on nearby predators, food, potential mates, and flocking."""
        
        # Scade cooldown-ul
        if self.reproduction_cooldown > 0:
            self.reproduction_cooldown -= 1
        
        # Dacă este în proces de împerechere
        if self.is_mating:
            self.mating_timer += 1
            if self.mating_timer >= self.mating_duration:
                self.ready_to_reproduce = True 
            self.base_speed = self.initial_base_speed
            
            # Rezoluția coliziunii nu este strict necesară aici, deoarece viteza este 0,
            # dar o lăsăm pentru siguranță dacă ar fi pornit de la o poziție ilegală.
            self.update_position() 
            self._resolve_obstacle_collision(obstacles) # NOU
            return 
        
        # PRIORITATE MAXIMĂ: EVITARE OBSTACOLE
        obstacle_force = self._obstacle_avoidance(obstacles)
        if obstacle_force.length_squared() > 0:
            self.velocity += obstacle_force
            if self.velocity.length_squared() != 0:
                self.velocity = self.velocity.normalize() 
            self.update_position()
            self._resolve_obstacle_collision(obstacles) # NOU
            return 

        # Vectorul de forță (accelerație)
        steering_force = pygame.math.Vector2(0, 0)

        # PRIORITATE 1: FUGĂ (dacă este urmărită)
        nearest_predator = self._find_nearest_predator(predators)
        if nearest_predator:
            flee_direction = (self.position - nearest_predator.position).normalize()
            steering_force = flee_direction * 1.0 
        
        # PRIORITATE 2: FLOCKING / REPRODUCERE / CĂUTARE HRANĂ
        elif self.can_reproduce(): 
            potential_mate = self._find_potential_mate(other_prey, self.mate_detection_radius)
            if potential_mate:
                self.seek_mate(potential_mate) 
            else:
                flocking_force = self._apply_flocking_behavior(other_prey)
                
                nearest_food = self._find_nearest_food(food_list)
                if nearest_food and self.energy < self.max_energy * 0.8:
                    food_direction = (nearest_food.position - self.position).normalize()
                    steering_force += food_direction * 0.1 
                else:
                    if random.random() < 0.05: 
                        vel = pygame.math.Vector2(random.uniform(-1, 1), random.uniform(-1, 1))
                        if vel.length_squared() != 0:
                            steering_force += vel.normalize() * WANDER_WEIGHT
                            
        else:
            self._apply_flocking_behavior(other_prey) 
            nearest_food = self._find_nearest_food(food_list)
            if nearest_food and self.energy < self.max_energy * 0.8:
                food_direction = (nearest_food.position - self.position).normalize()
                steering_force += food_direction * 0.1
            else:
                if random.random() < 0.05:
                    vel = pygame.math.Vector2(random.uniform(-1, 1), random.uniform(-1, 1))
                    if vel.length_squared() != 0:
                        steering_force += vel.normalize() * WANDER_WEIGHT


        # Aplică forța de steering (doar dacă nu s-a intrat în seek_mate)
        if not self.is_mating:
            self.velocity += steering_force
            if self.velocity.length_squared() != 0:
                self.velocity = self.velocity.normalize() 
            
            self.update_position()
            self._resolve_obstacle_collision(obstacles) # NOU
            

    def reproduce(self):
        """Create and return a new Prey agent (the offspring)."""
        offset = pygame.math.Vector2(random.uniform(-5, 5), random.uniform(-5, 5))
        child_sex = 'F' if random.random() < 0.5 else 'M'
        new_prey = Prey(sex=child_sex)
        new_prey.position = self.position.copy() + offset
        new_prey.energy = new_prey.max_energy * 1.0 
        return new_prey


    def _find_nearest_food(self, food_list):
        """Find the nearest food within detection radius."""
        nearest = None
        min_distance = self.food_detection_radius
        for food in food_list:
            distance = self.position.distance_to(food.position)
            if distance < min_distance:
                min_distance = distance
                nearest = food
        return nearest

    def move_towards_food(self, food):
        """Change velocity to move towards food."""
        direction = (food.position - self.position)
        if direction.length_squared() != 0:
            self.velocity = direction.normalize()

    def eat_food(self, energy_gain=30):
        """Gain energy from eating food."""
        self.energy = min(self.energy + energy_gain, self.max_energy)

    def _find_nearest_predator(self, predators):
        """Find the nearest predator within vision radius."""
        nearest = None
        min_distance = self.vision_radius
        for predator in predators:
            distance = self.position.distance_to(predator.position)
            if distance < min_distance:
                min_distance = distance
                nearest = predator
        return nearest

    def flee_from(self, predator):
        """Change velocity to flee away from the predator."""
        flee_direction = (self.position - predator.position)
        if flee_direction.length_squared() != 0:
            self.velocity = flee_direction.normalize()

    def draw(self):
        """Draw the prey as a circle with its trail, sex marker, and flocking circle (MODIFICARE AICI)."""
        
        # Desenarea cercului de Flocking dacă există vecini (flock_size > 1)
        if self.flock_size > 1:
            s = pygame.Surface((FLOCKING_RADIUS * 2, FLOCKING_RADIUS * 2), pygame.SRCALPHA)
            s.fill((0,0,0,0)) 
            pygame.draw.circle(
                s, 
                FLOCKING_CIRCLE_COLOR, 
                (FLOCKING_RADIUS, FLOCKING_RADIUS), 
                FLOCKING_RADIUS
            )
            screen.blit(s, (self.position.x - FLOCKING_RADIUS, self.position.y - FLOCKING_RADIUS))
            
        # Desenarea agentului Prey (cercul)
        pygame.draw.circle(screen, self.color, (int(self.position.x), int(self.position.y)), 4)
        
        # sex marker: mic cerc interior (doar pentru a vedea sexul)
        marker_color = FEMALE_MARKER_COLOR if self.sex == 'F' else MALE_MARKER_COLOR
        pygame.draw.circle(screen, marker_color, (int(self.position.x), int(self.position.y)), 2)
        
        self.draw_trail()
        self.draw_energy_bar()

# ==============================================================================
# CLASA PREDATOR (MODIFICARE: update - apel rezoluție coliziune)
# ==============================================================================
class Predator(Agent):
    """Class representing a predator agent."""
    def __init__(self, sex=None):
        # MODIFICARE: Durata de împerechere setată la 5 secunde
        super().__init__(speed=3, color=PREDATOR_COLOR, max_energy=150, sex=sex, mating_duration_sec=5)
        self.target_prey = None  # Prada pe care o urmărește în prezent
        self.mate_detection_radius = 80 # Raza de detectare pentru parteneri
        # predator_list va fi setat din Simulation înainte de update
        self.predator_list = []

    def can_reproduce(self):
        # Suprascrie doar pentru a folosi logica din baza (care include deja verificarea energiei)
        return super().can_reproduce()

    def reproduce(self):
        """Create and return a new Predator agent (the offspring)."""
        offset = pygame.math.Vector2(random.uniform(-5, 5), random.uniform(-5, 5))
        child_sex = 'F' if random.random() < 0.5 else 'M'
        new_predator = Predator(sex=child_sex)
        new_predator.position = self.position.copy() + offset
        new_predator.energy = new_predator.max_energy * 1.0 
        return new_predator

    def eat_prey(self, energy_gain=50):
        """Gain energy from eating prey."""
        self.energy = min(self.energy + energy_gain, self.max_energy)

    # MODIFICARE: Adaugă apelul self._resolve_obstacle_collision(obstacles)
    def update(self, prey_list, obstacles):
        """Update the predator's state based on nearby prey."""
        
        # Scade cooldown-ul
        if self.reproduction_cooldown > 0:
            self.reproduction_cooldown -= 1

        # Dacă este în proces de împerechere
        if self.is_mating:
            self.mating_timer += 1
            if self.mating_timer >= self.mating_duration:
                self.ready_to_reproduce = True
            self.update_position() 
            self._resolve_obstacle_collision(obstacles) # NOU
            return 
        
        # PRIORITATE MAXIMĂ: EVITARE OBSTACOLE
        obstacle_force = self._obstacle_avoidance(obstacles)
        if obstacle_force.length_squared() > 0:
            self.velocity += obstacle_force
            if self.velocity.length_squared() != 0:
                self.velocity = self.velocity.normalize() 
            self.update_position()
            self._resolve_obstacle_collision(obstacles) # NOU
            return 

        # Verifică dacă prada țintă încă există, nu mai e vie, sau a început să se împerecheze
        if self.target_prey and (self.target_prey not in prey_list or not self.target_prey.is_alive() or self.target_prey.is_mating):
            if self.target_prey and self.target_prey in prey_list:
                self.target_prey.is_targeted = False 
            self.target_prey = None
        
        # PRIORITATE 1: VÂNĂTOARE (dacă există pradă disponibilă și energie sub 90%)
        if self.energy < self.max_energy * 0.9 and prey_list: 
            if not self.target_prey:
                self.target_prey = self._find_nearest_free_prey(prey_list)
            
            if self.target_prey:
                self.hunt(self.target_prey) 
                self._resolve_obstacle_collision(obstacles) # NOU
                return 
        
        # PRIORITATE 2: REPRODUCERE
        if self.can_reproduce(): 
            potential_mate = self._find_potential_mate(
                [p for p in self.predator_list if p != self], 
                self.mate_detection_radius
            )
            if potential_mate:
                self.seek_mate(potential_mate)
                self.update_position()
                self._resolve_obstacle_collision(obstacles) # NOU
                return 

        # COMPORTAMENT DEFAULT: Rătăcire (Wander)
        if random.random() < 0.05: 
            vel = pygame.math.Vector2(random.uniform(-1, 1), random.uniform(-1, 1))
            if vel.length_squared() != 0:
                self.velocity = vel.normalize()
        
        self.update_position()
        self._resolve_obstacle_collision(obstacles) # NOU


    def _find_nearest_free_prey(self, prey_list):
        """Find the nearest prey that is not already targeted and not mating."""
        available_prey = [prey for prey in prey_list if not prey.is_targeted and not prey.is_mating]
        if available_prey:
            nearest = min(available_prey, key=lambda prey: self.position.distance_to(prey.position))
            nearest.is_targeted = True
            return nearest
        return None

    def hunt(self, prey):
        """Change velocity to move towards the prey."""
        direction = (prey.position - self.position)
        if direction.length_squared() != 0:
            self.velocity = direction.normalize()
        self.update_position()

    def draw(self):
        """Draw the predator as a rotated triangle with its trail and sex marker."""
        angle = self.velocity.angle_to(pygame.math.Vector2(1, 0))

        point_list = [
            pygame.math.Vector2(10, 0),  
            pygame.math.Vector2(-5, -5), 
            pygame.math.Vector2(-5, 5),  
        ]

        rotated_points = [self.position + p.rotate(-angle) for p in point_list]

        pygame.draw.polygon(screen, self.color, rotated_points)

        marker_offset = pygame.math.Vector2(12, 0).rotate(-angle)
        marker_pos = self.position + marker_offset
        marker_color = FEMALE_MARKER_COLOR if self.sex == 'F' else MALE_MARKER_COLOR
        pygame.draw.circle(screen, marker_color, (int(marker_pos.x), int(marker_pos.y)), 3)

        self.draw_trail()
        self.draw_energy_bar()

# ==============================================================================
# CLASA FOOD (FĂRĂ MODIFICĂRI)
# ==============================================================================
class Food:
    """Class representing food resources."""
    def __init__(self, position=None):
        self.position = position or pygame.math.Vector2(random.uniform(0, WIDTH), random.uniform(0, HEIGHT))
        self.color = FOOD_COLOR
        self.size = 3

    def draw(self):
        """Draw the food as a small square."""
        pygame.draw.circle(screen, self.color, (int(self.position.x), int(self.position.y)), self.size)

# ==============================================================================
# CLASA SIMULATION (MODIFICĂRI: History Tracking, Nașteri)
# ==============================================================================
class Simulation:
    """Class to manage the entire simulation."""
    def __init__(self, num_prey=50, num_predators=3, num_food=100, num_obstacles=10):
        self.prey_list = [Prey(sex=('F' if i < num_prey/2 else 'M')) for i in range(num_prey)]
        self.predator_list = [Predator(sex=('F' if i < num_predators/2 else 'M')) for i in range(num_predators)]
        self.food_list = [Food() for _ in range(num_food)]
        self.obstacles_list = [Obstacle() for _ in range(num_obstacles)] 
        self.running = True
        self.food_spawn_timer = 0
        self.food_spawn_interval = 30  
        
        # NOU: Atribute pentru History Tracking
        self.history = []
        self.timestep = 0
        self.prey_births_current_step = 0
        self.predator_births_current_step = 0

    def run(self):
        """Main loop of the simulation."""
        while self.running:
            clock.tick(FPS)
            self.handle_events()
            self.reset_prey_targeting()
            self.update_agents()
            self.handle_collisions()
            self.handle_reproduction() 
            self.remove_dead_agents()
            self.spawn_food()
            
            # NOU: Înregistrează datele la fiecare pas
            self._record_history()
            
            self.render()

        pygame.quit()
        # NOU: Afișează graficele la sfârșitul simulării
        self.show_history_graphs() 


    def handle_events(self):
        """Handle user input and events."""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_p:
                    self.add_prey()
                elif event.key == pygame.K_o:
                    self.add_predator()
                elif event.key == pygame.K_f:
                    self.add_food()
                elif event.key == pygame.K_a: 
                    self.add_obstacle() 

    def add_prey(self):
        """Add a new prey to the simulation."""
        sex = 'F' if random.random() < 0.5 else 'M'
        self.prey_list.append(Prey(sex=sex))

    def add_predator(self):
        """Add a new predator to the simulation."""
        sex = 'F' if random.random() < 0.5 else 'M'
        self.predator_list.append(Predator(sex=sex))

    def add_food(self):
        """Add new food to the simulation."""
        self.food_list.append(Food())
        
    def add_obstacle(self):
        """Add a new obstacle to the simulation."""
        self.obstacles_list.append(Obstacle())


    def reset_prey_targeting(self):
        """Reset the targeting flag for all prey before each update."""
        pass 

    def update_agents(self):
        """Update all agents in the simulation."""
        # Update predators
        for predator in self.predator_list:
            predator.predator_list = self.predator_list 
            predator.update(self.prey_list, self.obstacles_list) 

        # Update prey
        for prey in self.prey_list:
            other_prey = [p for p in self.prey_list if p != prey]
            prey.update(self.predator_list, self.food_list, other_prey, self.obstacles_list) 

        # Eliberare pentru Pradă
        mating_preys = [p for p in self.prey_list if p.just_started_mating]
        if mating_preys:
            for predator in self.predator_list:
                if predator.target_prey in mating_preys:
                    predator.target_prey.is_targeted = False
                    predator.target_prey = None
        
        # Eliberare pentru Prădători
        mating_predators = [p for p in self.predator_list if p.just_started_mating and p.target_prey]
        if mating_predators:
             for p in mating_predators:
                p.target_prey.is_targeted = False
                p.target_prey = None

    def handle_collisions(self):
        """Handle collisions between predators and prey, and prey with food."""
        # Predator eating prey
        for predator in self.predator_list:
            for prey in self.prey_list[:]:
                if predator.position.distance_to(prey.position) < 6:
                    if prey.is_mating:
                        if prey.mate_partner:
                            prey.mate_partner.is_mating = False
                            prey.mate_partner.mate_partner = None
                            prey.mate_partner.is_pregnant = False
                            prey.mate_partner.ready_to_reproduce = False
                            prey.mate_partner.just_started_mating = False
                        
                    predator.eat_prey()
                    if predator.target_prey == prey:
                        predator.target_prey = None
                    self.prey_list.remove(prey)
        
        # Prey eating food
        for prey in self.prey_list:
            for food in self.food_list[:]:
                if prey.position.distance_to(food.position) < 6 and not prey.is_mating: 
                    prey.eat_food()
                    self.food_list.remove(food)

    def handle_reproduction(self):
        """Handle the creation of new agents after mating completion."""
        new_prey = []
        new_predators = []

        # Procesare Reproducere (Prey)
        for prey in self.prey_list:
            if prey.ready_to_reproduce:
                if prey.is_pregnant:
                    if prey.finalize_mating(): 
                        new_prey.append(prey.reproduce())
                        # NOU: Contorizează nașterea
                        self.prey_births_current_step += 1 
                else:
                    prey.finalize_mating()
                
        # Procesare Reproducere (Predator)
        for predator in self.predator_list[:]:
            if predator.ready_to_reproduce:
                if predator.is_pregnant:
                    if predator.finalize_mating():
                        new_predators.append(predator.reproduce())
                        # NOU: Contorizează nașterea
                        self.predator_births_current_step += 1 
                else:
                    predator.finalize_mating()


        self.prey_list.extend(new_prey)
        self.predator_list.extend(new_predators)
        
    # NOU: Metoda pentru înregistrarea stării curente
    def _record_history(self):
        """Records the current state of the simulation."""
        self.history.append({
            'timestep': self.timestep,
            'prey_count': len(self.prey_list),
            'predator_count': len(self.predator_list),
            'food_count': len(self.food_list),
            'prey_births': self.prey_births_current_step,
            'predator_births': self.predator_births_current_step
        })
        self.timestep += 1
        
        # Resetăm contoarele de nașteri pentru pasul următor
        self.prey_births_current_step = 0
        self.predator_births_current_step = 0


    def remove_dead_agents(self):
        """Remove agents that have run out of energy."""
        
        for predator in self.predator_list:
            if not predator.is_alive() and predator.target_prey:
                predator.target_prey.is_targeted = False
                
        self.prey_list = [prey for prey in self.prey_list if prey.is_alive()]
        self.predator_list = [p for p in self.predator_list if p.is_alive()]


    def spawn_food(self):
        """Periodically spawn new food resources."""
        self.food_spawn_timer += 1
        if self.food_spawn_timer >= self.food_spawn_interval:
            self.food_spawn_timer = 0
            for _ in range(random.randint(1, 3)):
                self.food_list.append(Food())

    def render(self):
        """Render all elements on the screen."""
        screen.fill(BACKGROUND_COLOR)
        self.draw_legend()
        self.draw_stats()

        # Draw all food
        for food in self.food_list:
            food.draw()
            
        # Desenează obstacolele
        for obstacle in self.obstacles_list:
            obstacle.draw()

        # Draw all prey
        for prey in self.prey_list:
            prey.draw()

        # Draw all predators
        for predator in self.predator_list:
            predator.draw()

        pygame.display.flip()

    def draw_legend(self):
        """Draw the legend on the screen."""
        prey_text = FONT.render('Prey (Green Circle) - Press P to add', True, PREY_COLOR)
        predator_text = FONT.render('Predator (Red Triangle) - Press O to add', True, PREDATOR_COLOR)
        food_text = FONT.render('Food (Blue Circle) - Press F to add', True, FOOD_COLOR)
        obstacle_text = FONT.render('Obstacle (Grey Circle) - Press A to add', True, OBSTACLE_COLOR) 
        sex_legend_m = FONT.render('M (blue) - male', True, MALE_MARKER_COLOR)
        sex_legend_f = FONT.render('F (pink) - female', True, FEMALE_MARKER_COLOR)
        
        flocking_text = FONT.render(f'Flock (radius: {FLOCKING_RADIUS}px) - Green halo', True, PREY_COLOR) 
        
        screen.blit(prey_text, (10, 10))
        screen.blit(predator_text, (10, 30))
        screen.blit(food_text, (10, 50))
        screen.blit(obstacle_text, (10, 70)) 
        screen.blit(sex_legend_m, (10, 90))
        screen.blit(sex_legend_f, (10, 110))
        screen.blit(flocking_text, (10, 130))


    def draw_stats(self):
        """Draw the simulation statistics on the screen."""
        prey_count_text = FONT.render(f'Prey: {len(self.prey_list)}', True, TEXT_COLOR)
        predator_count_text = FONT.render(f'Predators: {len(self.predator_list)}', True, TEXT_COLOR)
        food_count_text = FONT.render(f'Food: {len(self.food_list)}', True, TEXT_COLOR)
        obstacle_count_text = FONT.render(f'Obstacles: {len(self.obstacles_list)}', True, TEXT_COLOR) 
        screen.blit(prey_count_text, (WIDTH - 150, 10))
        screen.blit(predator_count_text, (WIDTH - 150, 30))
        screen.blit(food_count_text, (WIDTH - 150, 50))
        screen.blit(obstacle_count_text, (WIDTH - 150, 70)) 
        
    # NOU: Metoda pentru afișarea graficelor
    def show_history_graphs(self):
        """Generates and displays graphs of the simulation history."""
        if not self.history:
            print("Nu există date de istoric de afișat.")
            return

        df = pd.DataFrame(self.history)
        
        # Converteste timesteps la secunde (pentru o axă X mai ușor de citit)
        df['time_sec'] = df['timestep'] / FPS

        # ======================================================================
        # Grafic 1: Schimbările populației în timp
        # ======================================================================
        plt.figure(figsize=(12, 6))
        plt.plot(df['time_sec'], df['prey_count'], label='Populație Pradă', color='green')
        plt.plot(df['time_sec'], df['predator_count'], label='Populație Prădător', color='red')
        plt.xlabel('Timp (Secunde)')
        plt.ylabel('Număr de Agenți')
        plt.title('Schimbarea Populației Pradă-Prădător în Timp')
        plt.legend()
        plt.grid(True)
        plt.show()

        # ======================================================================
        # Grafic 2: Ratele de naștere (Birth Rates)
        # ======================================================================
        # Calculăm rata de naștere ca o medie mobilă pentru a netezi variațiile pe pas
        # Folosim o fereastră de 30 de pași (~0.5 secunde)
        window_size = 30
        df['prey_birth_rate_smooth'] = df['prey_births'].rolling(window=window_size).mean()
        df['predator_birth_rate_smooth'] = df['predator_births'].rolling(window=window_size).mean()

        plt.figure(figsize=(12, 6))
        plt.plot(df['time_sec'], df['prey_birth_rate_smooth'], label=f'Rată de Naștere Pradă (Medie mobilă {window_size} pași)', color='lightgreen')
        plt.plot(df['time_sec'], df['predator_birth_rate_smooth'], label=f'Rată de Naștere Prădător (Medie mobilă {window_size} pași)', color='salmon')
        plt.xlabel('Timp (Secunde)')
        plt.ylabel(f'Nașteri / Pas (Medie mobilă {window_size})')
        plt.title('Rata de Naștere a Prăzii și Prădătorilor în Timp')
        plt.legend()
        plt.grid(True)
        plt.ylim(bottom=0) # Asigură că începe de la 0
        plt.show()

# ==============================================================================
# MAIN EXECUTION
# ==============================================================================
if __name__ == "__main__":
    simulation = Simulation()
    simulation.run()