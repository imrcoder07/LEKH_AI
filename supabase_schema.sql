-- Execute this script in your Supabase SQL Editor

-- 1. Create land_records table
CREATE TABLE IF NOT EXISTS public.land_records (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    "ULPIN" TEXT UNIQUE NOT NULL,
    "Owner_Token" TEXT NOT NULL,
    "Area" NUMERIC NOT NULL,
    "Geometry" JSONB
);

-- 2. Create land_ledger table
CREATE TABLE IF NOT EXISTS public.land_ledger (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    "Record_ID" UUID NOT NULL REFERENCES public.land_records(id) ON DELETE CASCADE,
    "Current_Hash" TEXT NOT NULL,
    "Previous_Hash" TEXT NOT NULL,
    "Timestamp" TIMESTAMPTZ DEFAULT NOW()
);

-- 3. Enable RLS
ALTER TABLE public.land_records ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.land_ledger ENABLE ROW LEVEL SECURITY;

-- 4. Establish Policies (Deny All by Default, Allow Service Role Exception)
-- We only want our authenticated super-admin backend script (using the Service Role key)
-- to be able to read and write records, strictly passing through our App logic for AES tokenization.

CREATE POLICY "Service Role Full Access on land_records" 
ON public.land_records
FOR ALL
USING (auth.role() = 'service_role')
WITH CHECK (auth.role() = 'service_role');

CREATE POLICY "Service Role Full Access on land_ledger" 
ON public.land_ledger
FOR ALL
USING (auth.role() = 'service_role')
WITH CHECK (auth.role() = 'service_role');
