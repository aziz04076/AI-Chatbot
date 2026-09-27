import React, { useEffect, useRef } from 'react';
import * as THREE from 'three';
import { AIState } from '../../types';
import { useTheme } from '../../context/ThemeContext';

interface ReactiveOrbProps {
  state: AIState;
}

export const ReactiveOrb: React.FC<ReactiveOrbProps> = ({ state }) => {
  const mountRef = useRef<HTMLDivElement>(null);
  const { theme } = useTheme();

  useEffect(() => {
    const container = mountRef.current;
    if (!container) return;

    const width = container.clientWidth || 130;
    const height = container.clientHeight || 130;

    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(45, width / height, 0.1, 100);
    camera.position.z = 3.2;

    const renderer = new THREE.WebGLRenderer({ alpha: true, antialias: true });
    renderer.setSize(width, height);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    container.innerHTML = '';
    container.appendChild(renderer.domElement);

    // Inner glowing sphere
    const geometry = new THREE.IcosahedronGeometry(1.05, 32);
    // Preserve initial vertex positions for procedural wave deformation
    const originalPositions = geometry.attributes.position.clone();

    // Material with wireframe & vertex shaders / glow
    const material = new THREE.MeshStandardMaterial({
      color: 0x00f2fe,
      roughness: 0.1,
      metalness: 0.8,
      wireframe: true,
      emissive: 0x005577,
      emissiveIntensity: 0.6,
    });

    const orb = new THREE.Mesh(geometry, material);
    scene.add(orb);

    // Outer glow ring
    const ringGeo = new THREE.TorusGeometry(1.4, 0.02, 16, 100);
    const ringMat = new THREE.MeshBasicMaterial({ color: 0x00f2fe, transparent: true, opacity: 0.4 });
    const ring = new THREE.Mesh(ringGeo, ringMat);
    ring.rotation.x = Math.PI / 2.3;
    scene.add(ring);

    // Lights
    const ambientLight = new THREE.AmbientLight(0xffffff, 1.2);
    scene.add(ambientLight);

    const pointLight = new THREE.PointLight(0x00f2fe, 3, 10);
    pointLight.position.set(2, 2, 2);
    scene.add(pointLight);

    let frameId: number;
    let clock = new THREE.Clock();

    const animate = () => {
      frameId = requestAnimationFrame(animate);
      const elapsedTime = clock.getElapsedTime();

      // State-based dynamics
      let rotationSpeed = 0.4;
      let waveFreq = 2.0;
      let waveAmp = 0.06;
      let targetColor = new THREE.Color(0x00f2fe);
      let ringColor = new THREE.Color(0x00f2fe);

      if (theme === 'cosmic') {
        targetColor = new THREE.Color(0x8b5cf6);
        ringColor = new THREE.Color(0xec4899);
      } else if (theme === 'minimal') {
        targetColor = new THREE.Color(0x38bdf8);
        ringColor = new THREE.Color(0x94a3b8);
      }

      if (state === 'thinking') {
        rotationSpeed = 2.2;
        waveFreq = 8.0;
        waveAmp = 0.16;
        targetColor = new THREE.Color(0xf59e0b); // Pulsing Amber/Gold
        ringColor = new THREE.Color(0xef4444);
      } else if (state === 'speaking') {
        rotationSpeed = 1.1;
        waveFreq = 5.0;
        waveAmp = 0.22; // Active sound wave ripple
        targetColor = new THREE.Color(0x10b981); // Radiant Emerald
        ringColor = new THREE.Color(0x06b6d4);
      }

      material.color.lerp(targetColor, 0.08);
      material.emissive.lerp(targetColor, 0.08);
      ringMat.color.lerp(ringColor, 0.08);

      orb.rotation.y += rotationSpeed * 0.015;
      orb.rotation.x += rotationSpeed * 0.01;
      ring.rotation.z += rotationSpeed * 0.02;

      // Surface vertex deformation (harmonic waves)
      const posAttr = geometry.attributes.position;
      const origPos = originalPositions.array;
      const currentPos = posAttr.array as Float32Array;

      for (let i = 0; i < origPos.length; i += 3) {
        const u = origPos[i];
        const v = origPos[i + 1];
        const w = origPos[i + 2];
        const dist = Math.sqrt(u * u + v * v + w * w);

        // Sinusoidal surface wave
        const wave = Math.sin(dist * waveFreq + elapsedTime * (state === 'speaking' ? 7.0 : 3.0)) * waveAmp;
        currentPos[i] = u * (1 + wave);
        currentPos[i + 1] = v * (1 + wave);
        currentPos[i + 2] = w * (1 + wave);
      }
      posAttr.needsUpdate = true;

      renderer.render(scene, camera);
    };

    animate();

    return () => {
      cancelAnimationFrame(frameId);
      renderer.dispose();
      geometry.dispose();
      material.dispose();
      ringGeo.dispose();
      ringMat.dispose();
    };
  }, [state, theme]);

  return (
    <div className="relative flex flex-col items-center justify-center">
      <div ref={mountRef} className="w-24 h-24 sm:w-28 sm:h-28 cursor-pointer" />
      <span className="text-[11px] font-mono tracking-wider uppercase text-cyan-300/80 mt-1 flex items-center gap-1.5">
        <span
          className={`w-2 h-2 rounded-full ${
            state === 'thinking'
              ? 'bg-amber-400 animate-ping'
              : state === 'speaking'
              ? 'bg-emerald-400 animate-pulse'
              : 'bg-cyan-400'
          }`}
        />
        {state}
      </span>
    </div>
  );
};
