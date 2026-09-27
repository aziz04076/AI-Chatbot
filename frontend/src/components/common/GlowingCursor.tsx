import React, { useEffect, useRef, useState } from 'react';

interface Particle {
  x: number;
  y: number;
  vx: number;
  vy: number;
  size: number;
  alpha: number;
  color: string;
}

export const GlowingCursor: React.FC = () => {
  const [isTouchDevice, setIsTouchDevice] = useState(false);
  const [isHoveringClickable, setIsHoveringClickable] = useState(false);
  const [isMouseDown, setIsMouseDown] = useState(false);
  const [isVisible, setIsVisible] = useState(false);

  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const mouseRef = useRef({ x: -100, y: -100 });
  const ringPosRef = useRef({ x: -100, y: -100 });
  const particlesRef = useRef<Particle[]>([]);

  useEffect(() => {
    // Disable custom cursor on touch/mobile devices
    if (window.matchMedia('(pointer: coarse)').matches || 'ontouchstart' in window) {
      setIsTouchDevice(true);
      return;
    }

    const handleMouseMove = (e: MouseEvent) => {
      mouseRef.current = { x: e.clientX, y: e.clientY };
      if (!isVisible) setIsVisible(true);

      // Check if hovering clickable element
      const target = e.target as HTMLElement | null;
      if (target) {
        const isClickable = Boolean(
          target.closest('button') ||
          target.closest('a') ||
          target.closest('input') ||
          target.closest('textarea') ||
          target.closest('[role="button"]') ||
          target.closest('.cursor-pointer')
        );
        setIsHoveringClickable(isClickable);
      }

      // Spawn trailing neon particles on mouse move
      if (Math.random() < 0.6) {
        const colors = ['#00f2fe', '#38bdf8', '#818cf8', '#c084fc'];
        particlesRef.current.push({
          x: e.clientX + (Math.random() - 0.5) * 6,
          y: e.clientY + (Math.random() - 0.5) * 6,
          vx: (Math.random() - 0.5) * 1.2,
          vy: (Math.random() - 0.5) * 1.2,
          size: Math.random() * 3 + 1.5,
          alpha: 0.8,
          color: colors[Math.floor(Math.random() * colors.length)],
        });
      }
    };

    const handleMouseDown = () => setIsMouseDown(true);
    const handleMouseUp = () => setIsMouseDown(false);
    const handleMouseLeave = () => setIsVisible(false);
    const handleMouseEnter = () => setIsVisible(true);

    window.addEventListener('mousemove', handleMouseMove);
    window.addEventListener('mousedown', handleMouseDown);
    window.addEventListener('mouseup', handleMouseUp);
    document.addEventListener('mouseleave', handleMouseLeave);
    document.addEventListener('mouseenter', handleMouseEnter);

    // Canvas particle loop and ring lerp
    let animId: number;
    const canvas = canvasRef.current;
    const ctx = canvas ? canvas.getContext('2d') : null;

    const resizeCanvas = () => {
      if (canvas) {
        canvas.width = window.innerWidth;
        canvas.height = window.innerHeight;
      }
    };
    resizeCanvas();
    window.addEventListener('resize', resizeCanvas);

    const render = () => {
      animId = requestAnimationFrame(render);

      // Smooth lerp for ring follower
      ringPosRef.current.x += (mouseRef.current.x - ringPosRef.current.x) * 0.18;
      ringPosRef.current.y += (mouseRef.current.y - ringPosRef.current.y) * 0.18;

      if (!ctx || !canvas) return;
      ctx.clearRect(0, 0, canvas.width, canvas.height);

      // Update and draw particles
      const particles = particlesRef.current;
      for (let i = particles.length - 1; i >= 0; i--) {
        const p = particles[i];
        p.x += p.vx;
        p.y += p.vy;
        p.alpha -= 0.025;
        p.size *= 0.96;

        if (p.alpha <= 0 || p.size <= 0.2) {
          particles.splice(i, 1);
          continue;
        }

        ctx.save();
        ctx.globalAlpha = p.alpha;
        ctx.fillStyle = p.color;
        ctx.shadowColor = p.color;
        ctx.shadowBlur = 8;
        ctx.beginPath();
        ctx.arc(p.x, p.y, p.size, 0, Math.PI * 2);
        ctx.fill();
        ctx.restore();
      }
    };

    animId = requestAnimationFrame(render);

    return () => {
      window.removeEventListener('mousemove', handleMouseMove);
      window.removeEventListener('mousedown', handleMouseDown);
      window.removeEventListener('mouseup', handleMouseUp);
      document.removeEventListener('mouseleave', handleMouseLeave);
      document.removeEventListener('mouseenter', handleMouseEnter);
      window.removeEventListener('resize', resizeCanvas);
      cancelAnimationFrame(animId);
    };
  }, [isVisible]);

  if (isTouchDevice || !isVisible) return null;

  return (
    <>
      {/* Particle Canvas */}
      <canvas
        ref={canvasRef}
        className="fixed inset-0 pointer-events-none z-50 overflow-hidden"
      />

      {/* Outer Magnetic Ring */}
      <div
        className="fixed pointer-events-none z-50 rounded-full transition-transform duration-75 ease-out -translate-x-1/2 -translate-y-1/2"
        style={{
          left: `${ringPosRef.current.x}px`,
          top: `${ringPosRef.current.y}px`,
          width: isHoveringClickable ? '48px' : isMouseDown ? '24px' : '34px',
          height: isHoveringClickable ? '48px' : isMouseDown ? '24px' : '34px',
          border: isHoveringClickable
            ? '1.5px solid rgba(0, 242, 254, 0.85)'
            : '1px solid rgba(0, 242, 254, 0.45)',
          backgroundColor: isHoveringClickable
            ? 'rgba(0, 242, 254, 0.12)'
            : 'rgba(0, 242, 254, 0.03)',
          boxShadow: isHoveringClickable
            ? '0 0 16px rgba(0, 242, 254, 0.45)'
            : '0 0 8px rgba(0, 242, 254, 0.2)',
          backdropFilter: isHoveringClickable ? 'blur(1px)' : 'none',
        }}
      />

      {/* Inner Pinpoint Glow Dot */}
      <div
        className="fixed pointer-events-none z-50 rounded-full bg-cyan-400 shadow-[0_0_8px_#00f2fe] -translate-x-1/2 -translate-y-1/2 transition-transform duration-75"
        style={{
          left: `${mouseRef.current.x}px`,
          top: `${mouseRef.current.y}px`,
          width: isMouseDown ? '6px' : '4px',
          height: isMouseDown ? '6px' : '4px',
        }}
      />
    </>
  );
};
