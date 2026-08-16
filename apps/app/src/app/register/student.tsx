import { useQuery } from '@tanstack/react-query';
import { Link, router } from 'expo-router';
import React, { useMemo, useState } from 'react';
import { Pressable, Text, View } from 'react-native';

import { ApiError } from '@/api/client';
import { endpoints, queryKeys } from '@/api/endpoints';
import type { CoachPublic, DominantFoot } from '@/api/types';
import {
  Badge,
  Brand,
  Button,
  Card,
  Chip,
  Field,
  Loading,
  Muted,
  Notice,
  Row,
  Screen,
  SectionTitle,
} from '@/components/ui';
import { useAuth } from '@/store/auth';
import { colors, font, radius, spacing } from '@/theme';

type Step = 0 | 1 | 2;
const STEP_LABELS = ['Account', 'Football profile', 'Guardian & consent'];

export default function RegisterStudent() {
  const { registerStudent, signingIn } = useAuth();
  const [step, setStep] = useState<Step>(0);
  const [error, setError] = useState<string | null>(null);

  // account
  const [fullName, setFullName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [phone, setPhone] = useState('');
  const [dob, setDob] = useState('');

  // football
  const [coachId, setCoachId] = useState<string | null>(null);
  const [batch, setBatch] = useState('');
  const [course, setCourse] = useState('Ball Mastery — Foundation');
  const [position, setPosition] = useState('');
  const [foot, setFoot] = useState<DominantFoot | null>(null);
  const [jersey, setJersey] = useState('');
  const [height, setHeight] = useState('');
  const [weight, setWeight] = useState('');
  const [yearsPlaying, setYearsPlaying] = useState('');
  const [previousClub, setPreviousClub] = useState('');

  // guardian
  const [guardianName, setGuardianName] = useState('');
  const [guardianPhone, setGuardianPhone] = useState('');
  const [guardianEmail, setGuardianEmail] = useState('');
  const [emergency, setEmergency] = useState('');
  const [school, setSchool] = useState('');
  const [medical, setMedical] = useState('');
  const [address, setAddress] = useState('');
  const [consent, setConsent] = useState(false);

  const coachesQuery = useQuery({ queryKey: queryKeys.coaches, queryFn: endpoints.coaches });
  const coaches = coachesQuery.data ?? [];
  const selectedCoach = useMemo(
    () => coaches.find((c) => c.id === coachId) ?? null,
    [coaches, coachId],
  );

  const number = (value: string) => {
    const parsed = Number(value.trim());
    return value.trim() && Number.isFinite(parsed) ? parsed : null;
  };

  const validateStep = (): string | null => {
    if (step === 0) {
      if (fullName.trim().length < 2) return 'Enter your full name.';
      if (!email.includes('@')) return 'Enter a valid email address.';
      if (password.length < 8) return 'Password must be at least 8 characters.';
      if (dob && !/^\d{4}-\d{2}-\d{2}$/.test(dob.trim()))
        return 'Date of birth must look like 2011-04-23.';
    }
    if (step === 1) {
      if (!coachId) return 'Choose your coach.';
      if (!batch.trim()) return 'Enter your batch, for example "Powai batch".';
    }
    return null;
  };

  const next = () => {
    const problem = validateStep();
    if (problem) {
      setError(problem);
      return;
    }
    setError(null);
    setStep((s) => Math.min(2, s + 1) as Step);
  };

  const submit = async () => {
    const problem = validateStep();
    if (problem) {
      setError(problem);
      return;
    }
    setError(null);
    try {
      await registerStudent({
        email: email.trim(),
        password,
        full_name: fullName.trim(),
        coach_id: coachId!,
        phone: phone.trim() || null,
        dob: dob.trim() || null,
        batch_name: batch.trim() || null,
        course: course.trim() || null,
        jersey_number: number(jersey),
        preferred_position: position.trim() || null,
        dominant_foot: foot,
        height_cm: number(height),
        weight_kg: number(weight),
        years_playing: number(yearsPlaying),
        previous_club: previousClub.trim() || null,
        school_name: school.trim() || null,
        guardian_name: guardianName.trim() || null,
        guardian_phone: guardianPhone.trim() || null,
        guardian_email: guardianEmail.trim() || null,
        emergency_contact: emergency.trim() || null,
        medical_notes: medical.trim() || null,
        address: address.trim() || null,
        consent_media: consent,
      });
      router.replace('/student');
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Registration failed. Please try again.');
      setStep(0);
    }
  };

  return (
    <Screen
      testID="register-student-screen"
      style={{ maxWidth: 560, width: '100%', alignSelf: 'center' }}
    >
      <View style={{ marginTop: spacing.xl, marginBottom: spacing.lg }}>
        <Brand subtitle="Student registration" />
      </View>

      <Row style={{ marginBottom: spacing.lg }} gap={spacing.sm}>
        {STEP_LABELS.map((label, index) => (
          <View key={label} style={{ flex: 1, gap: spacing.xs }}>
            <View
              style={{
                height: 3,
                borderRadius: 2,
                backgroundColor: index <= step ? colors.primary : colors.border,
              }}
            />
            <Text
              style={[
                font.label,
                { color: index === step ? colors.primary : colors.textFaint, fontSize: 10 },
              ]}
            >
              {label.toUpperCase()}
            </Text>
          </View>
        ))}
      </Row>

      {!!error && <Notice testID="register-error">{error}</Notice>}

      <Card>
        {step === 0 && (
          <>
            <Field
              label="Full name"
              testID="reg-name"
              value={fullName}
              onChangeText={setFullName}
              placeholder="Arjun Mehta"
              autoCapitalize="words"
            />
            <Field
              label="Email"
              testID="reg-email"
              value={email}
              onChangeText={setEmail}
              placeholder="you@example.com"
              keyboardType="email-address"
              autoCapitalize="none"
            />
            <Field
              label="Password"
              testID="reg-password"
              value={password}
              onChangeText={setPassword}
              placeholder="At least 8 characters"
              secure
              autoCapitalize="none"
            />
            <Field
              label="Phone"
              testID="reg-phone"
              value={phone}
              onChangeText={setPhone}
              placeholder="+91 98200 00000"
              keyboardType="phone-pad"
            />
            <Field
              label="Date of birth"
              testID="reg-dob"
              value={dob}
              onChangeText={setDob}
              placeholder="2011-04-23"
              hint="Format: YYYY-MM-DD"
              autoCapitalize="none"
            />
          </>
        )}

        {step === 1 && (
          <>
            <SectionTitle>Your coach</SectionTitle>
            {coachesQuery.isLoading ? (
              <Loading label="Loading coaches…" />
            ) : coaches.length === 0 ? (
              <Notice tone="warning">
                No coaches are registered yet. Ask the academy to add one, or register a coach
                account first.
              </Notice>
            ) : (
              <View style={{ gap: spacing.sm, marginBottom: spacing.lg }}>
                {coaches.map((coach) => (
                  <CoachOption
                    key={coach.id}
                    coach={coach}
                    selected={coachId === coach.id}
                    onSelect={() => {
                      setCoachId(coach.id);
                      if (!batch && coach.batches.length) setBatch(coach.batches[0]);
                    }}
                  />
                ))}
              </View>
            )}

            {!!selectedCoach?.batches.length && (
              <>
                <SectionTitle>Batch</SectionTitle>
                <Row style={{ flexWrap: 'wrap', marginBottom: spacing.md }} gap={spacing.sm}>
                  {selectedCoach.batches.map((name) => (
                    <Chip
                      key={name}
                      label={name}
                      selected={batch === name}
                      onPress={() => setBatch(name)}
                      testID={`batch-${name}`}
                    />
                  ))}
                </Row>
              </>
            )}

            <Field
              label="Batch name"
              testID="reg-batch"
              value={batch}
              onChangeText={setBatch}
              placeholder="Powai batch"
              hint="Free text — type your own if it isn't listed above."
            />
            <Field
              label="Course"
              testID="reg-course"
              value={course}
              onChangeText={setCourse}
              placeholder="Ball Mastery — Foundation"
            />

            <SectionTitle>Dominant foot</SectionTitle>
            <Row style={{ marginBottom: spacing.lg }} gap={spacing.sm}>
              {(['left', 'right', 'both'] as DominantFoot[]).map((option) => (
                <Chip
                  key={option}
                  label={option[0].toUpperCase() + option.slice(1)}
                  selected={foot === option}
                  onPress={() => setFoot(option)}
                  testID={`foot-${option}`}
                />
              ))}
            </Row>

            <Field
              label="Preferred position"
              testID="reg-position"
              value={position}
              onChangeText={setPosition}
              placeholder="Attacking midfielder"
            />
            <Row gap={spacing.md}>
              <View style={{ flex: 1 }}>
                <Field
                  label="Jersey no."
                  testID="reg-jersey"
                  value={jersey}
                  onChangeText={setJersey}
                  placeholder="10"
                  keyboardType="numeric"
                />
              </View>
              <View style={{ flex: 1 }}>
                <Field
                  label="Height (cm)"
                  value={height}
                  onChangeText={setHeight}
                  placeholder="162"
                  keyboardType="numeric"
                />
              </View>
              <View style={{ flex: 1 }}>
                <Field
                  label="Weight (kg)"
                  value={weight}
                  onChangeText={setWeight}
                  placeholder="48"
                  keyboardType="numeric"
                />
              </View>
            </Row>
            <Field
              label="Years playing"
              value={yearsPlaying}
              onChangeText={setYearsPlaying}
              placeholder="4"
              keyboardType="numeric"
            />
            <Field
              label="Previous club"
              value={previousClub}
              onChangeText={setPreviousClub}
              placeholder="Powai Juniors"
            />
          </>
        )}

        {step === 2 && (
          <>
            <Field
              label="Guardian name"
              testID="reg-guardian"
              value={guardianName}
              onChangeText={setGuardianName}
              placeholder="Mrs. Mehta"
              autoCapitalize="words"
            />
            <Field
              label="Guardian phone"
              value={guardianPhone}
              onChangeText={setGuardianPhone}
              placeholder="+91 98200 11111"
              keyboardType="phone-pad"
            />
            <Field
              label="Guardian email"
              value={guardianEmail}
              onChangeText={setGuardianEmail}
              placeholder="parent@example.com"
              keyboardType="email-address"
              autoCapitalize="none"
            />
            <Field
              label="Emergency contact"
              value={emergency}
              onChangeText={setEmergency}
              placeholder="+91 98200 22222"
              keyboardType="phone-pad"
            />
            <Field
              label="School"
              value={school}
              onChangeText={setSchool}
              placeholder="Bombay Scottish"
            />
            <Field
              label="Medical notes"
              value={medical}
              onChangeText={setMedical}
              placeholder="Allergies, injuries, anything the coach must know"
              multiline
            />
            <Field
              label="Address"
              value={address}
              onChangeText={setAddress}
              placeholder="Flat, building, area"
              multiline
            />

            <Pressable
              testID="reg-consent"
              accessibilityRole="checkbox"
              accessibilityState={{ checked: consent }}
              onPress={() => setConsent((c) => !c)}
              style={{
                flexDirection: 'row',
                gap: spacing.md,
                alignItems: 'flex-start',
                padding: spacing.md,
                borderRadius: radius.md,
                borderWidth: 1,
                borderColor: consent ? colors.primary : colors.border,
                backgroundColor: consent ? colors.primarySoft : colors.surfaceAlt,
              }}
            >
              <Text style={{ fontSize: 18, color: consent ? colors.primary : colors.textFaint }}>
                {consent ? '☑' : '☐'}
              </Text>
              <Text style={[font.bodySm, { color: colors.textMuted, flex: 1 }]}>
                I agree that training videos I upload may be reviewed by my coach and used by
                Pramonit Football Academy for coaching and progress tracking.
              </Text>
            </Pressable>
          </>
        )}

        <Row style={{ marginTop: spacing.lg }} gap={spacing.md}>
          {step > 0 && (
            <Button
              label="Back"
              variant="secondary"
              testID="reg-back"
              onPress={() => setStep((s) => (s - 1) as Step)}
            />
          )}
          <View style={{ flex: 1 }}>
            {step < 2 ? (
              <Button label="Continue" testID="reg-next" onPress={next} full />
            ) : (
              <Button
                label="Create my account"
                testID="reg-submit"
                onPress={submit}
                loading={signingIn}
                full
              />
            )}
          </View>
        </Row>
      </Card>

      <View style={{ marginTop: spacing.lg, alignItems: 'center' }}>
        <Link href="/login" asChild>
          <Pressable testID="link-login">
            <Muted>Already registered? Sign in</Muted>
          </Pressable>
        </Link>
      </View>
    </Screen>
  );
}

function CoachOption({
  coach,
  selected,
  onSelect,
}: {
  coach: CoachPublic;
  selected: boolean;
  onSelect: () => void;
}) {
  return (
    <Pressable
      testID={`coach-${coach.id}`}
      accessibilityRole="radio"
      accessibilityState={{ selected }}
      accessibilityLabel={`Coach ${coach.full_name}`}
      onPress={onSelect}
      style={{
        padding: spacing.md,
        borderRadius: radius.md,
        borderWidth: 1,
        borderColor: selected ? colors.primary : colors.border,
        backgroundColor: selected ? colors.primarySoft : colors.surfaceAlt,
        gap: 2,
      }}
    >
      <Row style={{ justifyContent: 'space-between' }}>
        <Text style={[font.h3, { color: colors.text }]}>{coach.full_name}</Text>
        {selected && <Badge label="Selected" tone="success" />}
      </Row>
      <Text style={[font.bodySm, { color: colors.textMuted }]}>
        {[coach.specialization, coach.primary_location].filter(Boolean).join(' · ')}
      </Text>
      <Text style={[font.bodySm, { color: colors.textFaint }]}>
        {coach.student_count} student{coach.student_count === 1 ? '' : 's'}
        {coach.batches.length ? ` · ${coach.batches.join(', ')}` : ''}
      </Text>
    </Pressable>
  );
}
