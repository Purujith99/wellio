-- ============================================================================
-- Wellio Persistence Schema (Profiles & Sessions)
-- ============================================================================

-- 1. Create user_profiles table
CREATE TABLE IF NOT EXISTS user_profiles (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  user_email TEXT NOT NULL REFERENCES users(email) ON DELETE CASCADE,
  -- Profile Data
  age INTEGER,
  gender TEXT,
  height DECIMAL(5,2), -- cm
  weight DECIMAL(5,2), -- kg
  diet TEXT,
  exercise TEXT,
  sleep DECIMAL(4,1), -- hours
  smoking TEXT,
  drinking TEXT,
  
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  
  -- Ensure one profile per user
  CONSTRAINT unique_user_profile UNIQUE (user_email)
);

-- 2. Create sessions table for cookie-based auth
CREATE TABLE IF NOT EXISTS sessions (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  user_email TEXT NOT NULL REFERENCES users(email) ON DELETE CASCADE,
  token UUID NOT NULL DEFAULT gen_random_uuid(),
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
  
  -- Ensure fast lookup by token
  CONSTRAINT unique_token UNIQUE (token)
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_user_profiles_email ON user_profiles(user_email);
CREATE INDEX IF NOT EXISTS idx_sessions_token ON sessions(token);
CREATE INDEX IF NOT EXISTS idx_sessions_email ON sessions(user_email);

-- Comments
COMMENT ON TABLE user_profiles IS 'Stores user health profile data (Age, Height, Weight etc.)';
COMMENT ON TABLE sessions IS 'Stores active login sessions for cookie-based authentication';

-- Disable RLS to ensure application can write to these tables
ALTER TABLE user_profiles DISABLE ROW LEVEL SECURITY;
ALTER TABLE sessions DISABLE ROW LEVEL SECURITY;
