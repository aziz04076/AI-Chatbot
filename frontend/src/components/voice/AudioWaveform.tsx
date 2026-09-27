import React, { useEffect, useRef } from 'react';

interface AudioWaveformProps {
  isRecording: boolean;
}

export const AudioWaveform: React.FC<AudioWaveformProps> = ({ isRecording }) => {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    if (!isRecording) return;
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    let animId: number;
    let phase = 0;

    const draw = () => {
      animId = requestAnimationFrame(draw);
      phase += 0.12;

      ctx.clearRect(0, 0, canvas.width, canvas.height);

      const width = canvas.width;
      const height = canvas.height;
      const centerY = height / 2;

      // Draw active multi-layered neon waveform
      const layers = [
        { color: 'rgba(0, 242, 254, 0.8)', speed: 1.0, amp: 14 },
        { color: 'rgba(121, 40, 202, 0.6)', speed: 1.4, amp: 10 },
        { color: 'rgba(255, 0, 128, 0.4)', speed: 0.8, amp: 6 },
      ];

      layers.forEach(({ color, speed, amp }) => {
        ctx.beginPath();
        ctx.strokeStyle = color;
        ctx.lineWidth = 2;

        for (let x = 0; x < width; x += 3) {
          const normX = x / width;
          const envelope = Math.sin(normX * Math.PI); // Pinches at the ends
          const y = centerY + Math.sin(normX * 16 + phase * speed) * amp * envelope;

          if (x === 0) ctx.moveTo(x, y);
          else ctx.lineTo(x, y);
        }
        ctx.stroke();
      });
    };

    draw();

    return () => {
      cancelAnimationFrame(animId);
    };
  }, [isRecording]);

  if (!isRecording) return null;

  return (
    <div className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-cyan-950/40 border border-cyan-500/40 backdrop-blur-md">
      <span className="w-2 h-2 rounded-full bg-rose-500 animate-ping" />
      <span className="text-xs font-mono text-cyan-300">Listening...</span>
      <canvas ref={canvasRef} width={100} height={24} className="w-24 h-6" />
    </div>
  );
};
