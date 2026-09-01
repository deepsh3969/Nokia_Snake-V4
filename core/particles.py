import random
import pygame


class Particle:

    def __init__(
        self,
        x,
        y
    ):

        self.x = x
        self.y = y

        self.vx = random.uniform(
            -100,
            100
        )

        self.vy = random.uniform(
            -100,
            100
        )

        self.life = random.uniform(
            0.3,
            0.7
        )

        self.size = random.randint(
            2,
            5
        )


class ParticleSystem:

    def __init__(self):

        self.particles = []

        self.color = (
            215,
            255,
            60
        )

    def explode(
        self,
        x,
        y
    ):

        for _ in range(18):

            self.particles.append(

                Particle(
                    x,
                    y
                )
            )

    def update(
        self,
        dt
    ):

        alive = []

        for particle in self.particles:

            particle.x += (
                particle.vx * dt
            )

            particle.y += (
                particle.vy * dt
            )

            particle.life -= dt

            if particle.life > 0:

                alive.append(
                    particle
                )

        self.particles = alive

    def draw(
        self,
        screen
    ):

        for particle in self.particles:

            pygame.draw.circle(

                screen,

                self.color,

                (
                    int(particle.x),
                    int(particle.y)
                ),

                particle.size
            )

    def clear(self):

        self.particles.clear()