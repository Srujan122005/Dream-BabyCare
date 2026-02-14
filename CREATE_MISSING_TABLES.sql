-- Create Missing Tables for Dream Baby Care
-- Copy this entire script to Supabase SQL Editor and run it

-- 1. appointments table
CREATE TABLE appointments (
  id BIGINT PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
  user_id TEXT NOT NULL REFERENCES users(email),
  doctor_id UUID NOT NULL REFERENCES doctors(id),
  appointment_time TEXT NOT NULL,
  type TEXT NOT NULL,
  status TEXT DEFAULT 'Pending',
  notes TEXT,
  created_at TEXT NOT NULL
);

-- 2. baby_tracker table
CREATE TABLE baby_tracker (
  id BIGINT PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
  user_id TEXT NOT NULL REFERENCES users(email),
  activity_type TEXT NOT NULL,
  start_time TEXT NOT NULL,
  end_time TEXT,
  notes TEXT,
  created_at TEXT NOT NULL
);

-- 3. reminders table
CREATE TABLE reminders (
  id BIGINT PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
  user_id TEXT NOT NULL REFERENCES users(email),
  message TEXT NOT NULL,
  remind_time TEXT NOT NULL,
  created_at TEXT NOT NULL
);

-- Tables created!
