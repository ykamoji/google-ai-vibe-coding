'use client';

import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'motion/react';
import { Snowflake } from 'lucide-react';

interface Particle {
  id: string;
  x: number;
  delay: number;
  duration: number;
  sway: number;
}

export default function Home() {
  const [isSnowing, setIsSnowing] = useState(false);
  const [isBallooning, setIsBallooning] = useState(false);

  const handleSnowflakes = () => {
    setIsSnowing(true);
    setTimeout(() => {
      setIsSnowing(false);
    }, 5000);
  };

  const handleBalloons = () => {
    setIsBallooning(true);
    setTimeout(() => {
      setIsBallooning(false);
    }, 5000);
  };

  return (
    <main className="min-h-screen bg-[#0A0A0A] text-[#E8E4DF] flex flex-col justify-center relative overflow-hidden font-sans border-2 border-[#2A2A2A]">
      <div className="absolute left-[80px] top-0 bottom-0 w-[1px] bg-[#2A2A2A] hidden md:block" />
      <div className="absolute top-[120px] left-0 right-0 h-[1px] bg-[#2A2A2A] hidden md:block" />
      <div
        className="absolute left-[26px] top-1/2 -translate-y-1/2 -rotate-180 font-mono text-[10px] uppercase tracking-[4px] opacity-40 hidden md:block whitespace-nowrap"
        style={{ writingMode: 'vertical-rl' }}
      >
        Atmospheric Engine / AR-09
      </div>

      <header className="absolute top-0 left-0 right-0 h-[120px] pl-[40px] md:pl-[120px] pr-[40px] flex justify-between items-center z-10 w-full hidden sm:flex">
        <h2 className="font-serif italic text-[20px] tracking-[1px] font-normal">Celestial Dynamics</h2>
        <div className="font-mono text-[9px] uppercase tracking-[2px] opacity-60">Node: Active // Latency: 14ms</div>
      </header>

      <div className="z-10 bg-transparent text-left max-w-full w-full px-8 md:pl-[160px]">
        <p className="font-mono text-[10px] tracking-[5px] opacity-40 mb-5 uppercase">
          Module 01: Elements
        </p>
        <h1 className="text-5xl md:text-[72px] font-serif font-normal leading-[0.95] mb-5 md:mb-[30px] max-w-[600px]">
          <span className="block opacity-50 text-2xl md:text-[32px] mb-2.5">Sublime</span>
          Atmospheric Controls
        </h1>
        <p className="text-[#E8E4DF] opacity-60 mb-[60px] text-sm font-sans max-w-md">
          Trigger atmospheric effects. The selected sequence will run for 5 seconds.
        </p>

        <div className="flex flex-col sm:flex-row gap-10">
          <button
            onClick={handleSnowflakes}
            disabled={isSnowing || isBallooning}
            className="px-[48px] py-[20px] bg-transparent text-[#E8E4DF] border border-[#4A4A4A] hover:bg-[#E8E4DF] hover:text-[#0A0A0A] hover:border-[#E8E4DF] hover:-translate-y-[2px] active:translate-y-0 disabled:opacity-50 disabled:cursor-not-allowed transition-all duration-400 ease-[cubic-bezier(0.16,1,0.3,1)] uppercase tracking-[4px] text-[11px] font-mono cursor-pointer"
          >
            Snowflakes
          </button>
          <button
            onClick={handleBalloons}
            disabled={isSnowing || isBallooning}
            className="px-[48px] py-[20px] bg-transparent text-[#E8E4DF] border border-[#4A4A4A] hover:bg-[#E8E4DF] hover:text-[#0A0A0A] hover:border-[#E8E4DF] hover:-translate-y-[2px] active:translate-y-0 disabled:opacity-50 disabled:cursor-not-allowed transition-all duration-400 ease-[cubic-bezier(0.16,1,0.3,1)] uppercase tracking-[4px] text-[11px] font-mono cursor-pointer"
          >
            Balloons
          </button>
        </div>
      </div>

      <footer className="absolute bottom-0 left-0 right-0 h-[80px] pl-[40px] md:pl-[120px] pr-[40px] flex justify-between items-center border-t border-[#2A2A2A] font-mono text-[9px] opacity-30 uppercase tracking-[2px] hidden sm:flex">
        <div>Est. 2024 System Interface</div>
        <div>40.7128 N / 74.0060 W</div>
      </footer>

      <AnimatePresence>
        {isSnowing && <SnowflakesEffect />}
      </AnimatePresence>

      <AnimatePresence>
        {isBallooning && <BalloonsEffect />}
      </AnimatePresence>
    </main>
  );
}

function SnowflakesEffect() {
  const [particles, setParticles] = useState<Particle[]>([]);

  useEffect(() => {
    const newParticles: Particle[] = Array.from({ length: 70 }).map((_, i) => ({
      id: `snow-${i}`,
      x: Math.random() * 100,
      delay: Math.random() * 4,
      duration: 3 + Math.random() * 2,
      sway: (Math.random() - 0.5) * 100,
    }));
    const timer = setTimeout(() => setParticles(newParticles), 0);
    return () => clearTimeout(timer);
  }, []);

  return (
    <motion.div
      initial={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      transition={{ duration: 1 }}
      className="absolute inset-0 pointer-events-none"
    >
      {particles.map((p) => (
        <motion.div
          key={p.id}
          initial={{ top: '-10%', left: `${p.x}%`, opacity: 0, rotate: 0 }}
          animate={{
            top: '110%',
            opacity: [0, 1, 1, 0],
            rotate: 360,
            x: [0, p.sway, -p.sway, 0]
          }}
          transition={{
            duration: p.duration,
            delay: p.delay,
            ease: "linear"
          }}
          className="absolute text-[#E8E4DF] drop-shadow-sm opacity-80"
        >
          <Snowflake size={32} />
        </motion.div>
      ))}
    </motion.div>
  );
}

function BalloonsEffect() {
  const [particles, setParticles] = useState<Particle[]>([]);

  useEffect(() => {
    const newParticles: Particle[] = Array.from({ length: 30 }).map((_, i) => ({
      id: `balloon-${i}`,
      x: 5 + Math.random() * 90,
      delay: Math.random() * 3,
      duration: 4 + Math.random() * 2,
      sway: (Math.random() - 0.5) * 60,
    }));
    const timer = setTimeout(() => setParticles(newParticles), 0);
    return () => clearTimeout(timer);
  }, []);

  const balloonColors = ['text-[#E8E4DF]', 'text-[#C8C4BF]', 'text-[#A8A49F]', 'text-[#88847F]', 'text-[#68645F]'];

  return (
    <motion.div
      initial={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      transition={{ duration: 1 }}
      className="absolute inset-0 pointer-events-none"
    >
      {particles.map((p, i) => (
        <motion.div
          key={p.id}
          initial={{ bottom: '-20%', left: `${p.x}%`, opacity: 0 }}
          animate={{
            bottom: '120%',
            opacity: [0, 1, 1, 0],
            x: [0, p.sway, -p.sway, 0]
          }}
          transition={{
            duration: p.duration,
            delay: p.delay,
            ease: "linear"
          }}
          className={`absolute ${balloonColors[i % balloonColors.length]}`}
        >
          <svg
            width="40"
            height="60"
            viewBox="0 0 40 60"
            fill="none"
            xmlns="http://www.w3.org/2000/svg"
            className="drop-shadow-md opacity-90"
          >
            <path d="M20 1C9 1 1 10 1 21C1 34 20 45 20 45C20 45 39 34 39 21C39 10 31 1 20 1Z" fill="currentColor" />
            <path d="M20 45L16 50H24L20 45Z" fill="currentColor" />
            <path d="M20 50C20 50 15 55 20 60" stroke="#4A4A4A" strokeWidth="1.5" fill="none"/>
          </svg>
        </motion.div>
      ))}
    </motion.div>
  );
}
