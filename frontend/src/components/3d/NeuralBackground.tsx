import React, { useEffect, useRef } from 'react';
import * as THREE from 'three';
import { useTheme } from '../../context/ThemeContext';
import { AIState } from '../../types';

interface NeuralBackgroundProps {
  aiState?: AIState;
}

export const NeuralBackground: React.FC<NeuralBackgroundProps> = ({ aiState = 'idle' }) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const { theme } = useTheme();
  const aiStateRef = useRef<AIState>(aiState);
  aiStateRef.current = aiState;

  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    // Scene, Camera, Renderer
    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(60, window.innerWidth / window.innerHeight, 1, 1000);
    camera.position.z = 220;

    const renderer = new THREE.WebGLRenderer({ alpha: true, antialias: true });
    renderer.setSize(window.innerWidth, window.innerHeight);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    container.innerHTML = '';
    container.appendChild(renderer.domElement);

    // Particle setup
    const particleCount = 130;
    const positions = new Float32Array(particleCount * 3);
    const initialPositions = new Float32Array(particleCount * 3);
    const scales = new Float32Array(particleCount);
    const velocities: THREE.Vector3[] = [];

    const bounds = 150;
    for (let i = 0; i < particleCount; i++) {
      const x = (Math.random() - 0.5) * bounds * 2;
      const y = (Math.random() - 0.5) * bounds * 1.5;
      const z = (Math.random() - 0.5) * bounds;

      positions[i * 3] = x;
      positions[i * 3 + 1] = y;
      positions[i * 3 + 2] = z;

      initialPositions[i * 3] = x;
      initialPositions[i * 3 + 1] = y;
      initialPositions[i * 3 + 2] = z;

      scales[i] = 2.5 + Math.random() * 2.5;

      velocities.push(
        new THREE.Vector3(
          (Math.random() - 0.5) * 0.25,
          (Math.random() - 0.5) * 0.25,
          (Math.random() - 0.5) * 0.2
        )
      );
    }

    const geometry = new THREE.BufferGeometry();
    geometry.setAttribute('position', new THREE.BufferAttribute(positions, 3));
    geometry.setAttribute('a_scale', new THREE.BufferAttribute(scales, 1));

    // Theme color palettes
    const getColors = () => {
      if (theme === 'cosmic') {
        return {
          idle: new THREE.Color(0x8b5cf6),     // Cosmic purple
          thinking: new THREE.Color(0xf59e0b), // Amber
          speaking: new THREE.Color(0x06b6d4), // Cyan
          line: new THREE.Color(0x6366f1)
        };
      } else if (theme === 'minimal') {
        return {
          idle: new THREE.Color(0x38bdf8),     // Sky
          thinking: new THREE.Color(0xf97316), // Orange
          speaking: new THREE.Color(0x10b981), // Emerald
          line: new THREE.Color(0x64748b)
        };
      }
      return {
        idle: new THREE.Color(0x00f2fe),       // Cyber cyan
        thinking: new THREE.Color(0xf59e0b),   // Golden amber
        speaking: new THREE.Color(0x10b981),   // Emerald neon
        line: new THREE.Color(0x00f2fe)
      };
    };

    const colors = getColors();

    // Custom GLSL Shader Material
    const uniforms = {
      u_time: { value: 0.0 },
      u_state: { value: 0.0 }, // 0.0 = idle, 1.0 = thinking, 2.0 = speaking
      u_color_idle: { value: colors.idle },
      u_color_thinking: { value: colors.thinking },
      u_color_speaking: { value: colors.speaking },
    };

    const vertexShader = `
      uniform float u_time;
      uniform float u_state;
      attribute float a_scale;
      varying vec3 v_position;

      void main() {
        vec3 pos = position;

        // Swirling vortex dynamics when thinking (u_state close to 1.0)
        if (u_state > 0.05) {
          float distFromCenter = length(pos.xy);
          float angle = u_time * 0.8 * u_state * (1.0 / (distFromCenter * 0.02 + 1.0));
          float s = sin(angle);
          float c = cos(angle);
          pos.xy = mat2(c, -s, s, c) * pos.xy;
        }

        // Harmonic ripple waves when speaking (u_state close to 2.0)
        if (u_state > 1.05) {
          float ripple = sin(length(pos.xy) * 0.06 - u_time * 3.5) * 8.0 * (u_state - 1.0);
          pos.z += ripple;
        }

        // Subtle ambient organic breathing
        pos.x += sin(u_time * 0.6 + position.y * 0.03) * 2.5;
        pos.y += cos(u_time * 0.6 + position.x * 0.03) * 2.5;

        v_position = pos;
        vec4 mvPosition = modelViewMatrix * vec4(pos, 1.0);
        gl_Position = projectionMatrix * mvPosition;

        float size = a_scale * (240.0 / -mvPosition.z);
        gl_PointSize = clamp(size * (1.0 + 0.25 * sin(u_time * 2.0 + position.x * 0.1)), 2.0, 36.0);
      }
    `;

    const fragmentShader = `
      uniform float u_time;
      uniform float u_state;
      uniform vec3 u_color_idle;
      uniform vec3 u_color_thinking;
      uniform vec3 u_color_speaking;

      varying vec3 v_position;

      void main() {
        vec2 coord = gl_PointCoord - vec2(0.5);
        float dist = length(coord);
        if (dist > 0.5) discard;

        float alpha = smoothstep(0.5, 0.05, dist);

        // State-based color blending
        vec3 color = u_color_idle;
        if (u_state <= 1.0) {
          color = mix(u_color_idle, u_color_thinking, u_state);
        } else {
          color = mix(u_color_thinking, u_color_speaking, u_state - 1.0);
        }

        // Bright energetic core
        float core = smoothstep(0.18, 0.0, dist);
        color += vec3(0.4, 0.4, 0.5) * core;

        gl_FragColor = vec4(color, alpha * 0.9);
      }
    `;

    const shaderMaterial = new THREE.ShaderMaterial({
      vertexShader,
      fragmentShader,
      uniforms,
      transparent: true,
      blending: THREE.AdditiveBlending,
      depthWrite: false,
    });

    const particles = new THREE.Points(geometry, shaderMaterial);
    scene.add(particles);

    // Line network geometry
    const lineMaterial = new THREE.LineBasicMaterial({
      color: colors.line,
      transparent: true,
      opacity: 0.16,
      blending: THREE.AdditiveBlending,
    });

    const lineGeometry = new THREE.BufferGeometry();
    const linePositions = new Float32Array(particleCount * particleCount * 6);
    lineGeometry.setAttribute('position', new THREE.BufferAttribute(linePositions, 3));
    const lines = new THREE.LineSegments(lineGeometry, lineMaterial);
    scene.add(lines);

    // Mouse movement reactivity
    let mouseX = 0;
    let mouseY = 0;
    let targetX = 0;
    let targetY = 0;

    const onMouseMove = (e: MouseEvent) => {
      mouseX = (e.clientX - window.innerWidth / 2) * 0.04;
      mouseY = (e.clientY - window.innerHeight / 2) * 0.04;
    };
    window.addEventListener('mousemove', onMouseMove);

    // Resize handler
    const onResize = () => {
      camera.aspect = window.innerWidth / window.innerHeight;
      camera.updateProjectionMatrix();
      renderer.setSize(window.innerWidth, window.innerHeight);
    };
    window.addEventListener('resize', onResize);

    // Animation Loop
    let animationFrameId: number;
    let clock = new THREE.Clock();

    const animate = () => {
      animationFrameId = requestAnimationFrame(animate);
      const elapsedTime = clock.getElapsedTime();
      uniforms.u_time.value = elapsedTime;

      // Target state translation
      let targetStateValue = 0.0; // idle
      if (aiStateRef.current === 'thinking') targetStateValue = 1.0;
      else if (aiStateRef.current === 'speaking') targetStateValue = 2.0;

      // Smooth state interpolation (lerp)
      uniforms.u_state.value += (targetStateValue - uniforms.u_state.value) * 0.06;

      // Update line color / opacity to reflect active state
      if (uniforms.u_state.value > 0.5 && uniforms.u_state.value <= 1.5) {
        lineMaterial.color.lerp(colors.thinking, 0.05);
        lineMaterial.opacity = 0.24;
      } else if (uniforms.u_state.value > 1.5) {
        lineMaterial.color.lerp(colors.speaking, 0.05);
        lineMaterial.opacity = 0.22;
      } else {
        lineMaterial.color.lerp(colors.line, 0.05);
        lineMaterial.opacity = 0.16;
      }

      // Smooth camera interpolation
      targetX += (mouseX - targetX) * 0.05;
      targetY += (mouseY - targetY) * 0.05;
      camera.position.x = targetX;
      camera.position.y = -targetY;
      camera.lookAt(scene.position);

      const pos = geometry.attributes.position.array as Float32Array;
      for (let i = 0; i < particleCount; i++) {
        // Accelerate velocities slightly when thinking
        const speedMult = 1.0 + (uniforms.u_state.value > 0.5 ? 0.6 : 0.0);
        pos[i * 3] += velocities[i].x * speedMult;
        pos[i * 3 + 1] += velocities[i].y * speedMult;
        pos[i * 3 + 2] += velocities[i].z * speedMult;

        // Bounce on boundary
        if (Math.abs(pos[i * 3]) > bounds) velocities[i].x *= -1;
        if (Math.abs(pos[i * 3 + 1]) > bounds * 0.75) velocities[i].y *= -1;
        if (Math.abs(pos[i * 3 + 2]) > bounds * 0.5) velocities[i].z *= -1;
      }
      geometry.attributes.position.needsUpdate = true;

      // Update neural network connecting lines
      let lineIdx = 0;
      const lPos = lineGeometry.attributes.position.array as Float32Array;
      const connectDist = 38;

      for (let i = 0; i < particleCount; i++) {
        for (let j = i + 1; j < particleCount; j++) {
          const dx = pos[i * 3] - pos[j * 3];
          const dy = pos[i * 3 + 1] - pos[j * 3 + 1];
          const dz = pos[i * 3 + 2] - pos[j * 3 + 2];
          const dist = Math.sqrt(dx * dx + dy * dy + dz * dz);

          if (dist < connectDist) {
            lPos[lineIdx++] = pos[i * 3];
            lPos[lineIdx++] = pos[i * 3 + 1];
            lPos[lineIdx++] = pos[i * 3 + 2];

            lPos[lineIdx++] = pos[j * 3];
            lPos[lineIdx++] = pos[j * 3 + 1];
            lPos[lineIdx++] = pos[j * 3 + 2];
          }
        }
      }
      lineGeometry.setDrawRange(0, lineIdx / 3);
      lineGeometry.attributes.position.needsUpdate = true;

      renderer.render(scene, camera);
    };

    animate();

    return () => {
      cancelAnimationFrame(animationFrameId);
      window.removeEventListener('mousemove', onMouseMove);
      window.removeEventListener('resize', onResize);
      renderer.dispose();
      geometry.dispose();
      lineGeometry.dispose();
      shaderMaterial.dispose();
      lineMaterial.dispose();
    };
  }, [theme]);

  return <div ref={containerRef} className="fixed inset-0 pointer-events-none z-0 overflow-hidden" />;
};
