import { Link, router } from 'expo-router';
import React, { useState } from 'react';
import { Pressable, Text, View } from 'react-native';

import { ApiError } from '@/api/client';
import {
  Brand,
  Button,
  Card,
  Chip,
  Field,
  Muted,
  Notice,
  Row,
  Screen,
  SectionTitle,
} from '@/components/ui';
import { useAuth } from '@/store/auth';
import { colors, font, spacing } from '@/theme';

export default function RegisterCoach() {
  const { registerCoach, signingIn } = useAuth();
  const [error, setError] = useState<string | null>(null);

  const [fullName, setFullName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [phone, setPhone] = useState('');
  const [specialization, setSpecialization] = useState('');
  const [location, setLocation] = useState('');
  const [experience, setExperience] = useState('');
  const [qualifications, setQualifications] = useState('');
  const [bio, setBio] = useState('');
  const [batchInput, setBatchInput] = useState('');
  const [batches, setBatches] = useState<string[]>([]);

  const addBatch = () => {
    const name = batchInput.trim();
    if (!name || batches.includes(name)) return;
    setBatches((current) => [...current, name]);
    setBatchInput('');
  };

  const submit = async () => {
    setError(null);
    if (fullName.trim().length < 2) return setError('Enter your full name.');
    if (!email.includes('@')) return setError('Enter a valid email address.');
    if (password.length < 8) return setError('Password must be at least 8 characters.');

    const years = Number(experience.trim());
    try {
      await registerCoach({
        email: email.trim(),
        password,
        full_name: fullName.trim(),
        phone: phone.trim() || null,
        specialization: specialization.trim() || null,
        primary_location: location.trim() || null,
        years_experience: experience.trim() && Number.isFinite(years) ? years : null,
        qualifications: qualifications.trim() || null,
        bio: bio.trim() || null,
        batches,
      });
      router.replace('/coach');
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Registration failed. Please try again.');
    }
  };

  return (
    <Screen
      testID="register-coach-screen"
      style={{ maxWidth: 560, width: '100%', alignSelf: 'center' }}
    >
      <View style={{ marginTop: spacing.xl, marginBottom: spacing.lg }}>
        <Brand subtitle="Coach registration" />
      </View>

      {!!error && <Notice testID="register-error">{error}</Notice>}

      <Card>
        <Field
          label="Full name"
          testID="coach-name"
          value={fullName}
          onChangeText={setFullName}
          placeholder="Rahul Menon"
          autoCapitalize="words"
        />
        <Field
          label="Email"
          testID="coach-email"
          value={email}
          onChangeText={setEmail}
          placeholder="coach@example.com"
          keyboardType="email-address"
          autoCapitalize="none"
        />
        <Field
          label="Password"
          testID="coach-password"
          value={password}
          onChangeText={setPassword}
          placeholder="At least 8 characters"
          secure
          autoCapitalize="none"
        />
        <Field
          label="Phone"
          value={phone}
          onChangeText={setPhone}
          placeholder="+91 98200 00000"
          keyboardType="phone-pad"
        />
        <Field
          label="Specialization"
          testID="coach-specialization"
          value={specialization}
          onChangeText={setSpecialization}
          placeholder="Ball mastery & first touch"
        />
        <Field
          label="Primary location"
          testID="coach-location"
          value={location}
          onChangeText={setLocation}
          placeholder="Powai"
        />
        <Field
          label="Years of experience"
          value={experience}
          onChangeText={setExperience}
          placeholder="9"
          keyboardType="numeric"
        />
        <Field
          label="Qualifications"
          value={qualifications}
          onChangeText={setQualifications}
          placeholder="AFC 'C' Licence, AIFF Grassroots"
        />
        <Field
          label="About you"
          value={bio}
          onChangeText={setBio}
          placeholder="A line students and parents will see."
          multiline
        />

        <SectionTitle>Your batches</SectionTitle>
        <Muted style={{ marginBottom: spacing.sm }}>
          These appear on the student signup screen. Add as many as you run.
        </Muted>
        <Row gap={spacing.sm} style={{ alignItems: 'flex-start' }}>
          <View style={{ flex: 1 }}>
            <Field
              label="Batch name"
              testID="coach-batch-input"
              value={batchInput}
              onChangeText={setBatchInput}
              placeholder="Powai batch"
            />
          </View>
          <View style={{ paddingTop: 22 }}>
            <Button label="Add" testID="coach-batch-add" variant="secondary" onPress={addBatch} small />
          </View>
        </Row>

        {batches.length > 0 && (
          <Row style={{ flexWrap: 'wrap', marginBottom: spacing.md }} gap={spacing.sm}>
            {batches.map((name) => (
              <Chip
                key={name}
                label={`${name}  ✕`}
                selected
                testID={`coach-batch-${name}`}
                onPress={() => setBatches((current) => current.filter((b) => b !== name))}
              />
            ))}
          </Row>
        )}

        <Button
          label="Create coach account"
          testID="coach-submit"
          onPress={submit}
          loading={signingIn}
          full
          style={{ marginTop: spacing.md }}
        />
      </Card>

      <View style={{ marginTop: spacing.lg, alignItems: 'center', gap: spacing.sm }}>
        <Link href="/login" asChild>
          <Pressable testID="link-login">
            <Muted>Already registered? Sign in</Muted>
          </Pressable>
        </Link>
        <Link href="/register/student" asChild>
          <Pressable>
            <Text style={[font.bodySm, { color: colors.primary }]}>
              I'm a student instead →
            </Text>
          </Pressable>
        </Link>
      </View>
    </Screen>
  );
}
