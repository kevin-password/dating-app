import random
from datetime import date, timedelta
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from core.models import Profile, Preference, Like, Match, Pass

class Command(BaseCommand):
    help = 'Seeds the database with test users, profiles, and mock matches'

    def handle(self, *args, **kwargs):
        self.stdout.write(self.style.WARNING('Starting database seeding...'))

        # 1. Clean up previous test users (to prevent duplicates on re-runs)
        User.objects.filter(username__startswith='testuser_').delete()
        self.stdout.write(self.style.SUCCESS('Cleared old test users.'))

        # 2. Data pools for realistic generation
        first_names_male = ['James', 'John', 'Robert', 'Michael', 'William', 'David', 'Richard', 'Joseph']
        first_names_female = ['Mary', 'Patricia', 'Jennifer', 'Linda', 'Elizabeth', 'Susan', 'Jessica', 'Sarah']
        cities = ['New York', 'Los Angeles', 'Chicago', 'Houston', 'Phoenix', 'London', 'Paris', 'Toronto']
        bios = [
            "Love hiking, coffee, and good conversations. ☕🏔️",
            "Just looking for someone to share pizza with. 🍕",
            "Tech nerd by day, gamer by night. Let's match! 🎮",
            "Travel enthusiast. Next stop: Japan! ✈️",
            "Dog mom/dad. My pet is probably cuter than me. 🐶",
            "Fitness junkie and amateur chef. 🏋️‍♂️🍳"
        ]

        created_users = []

        # 3. Create 15 Test Users
        for i in range(1, 16):
            gender = random.choice(['male', 'female'])
            first_name = random.choice(first_names_male if gender == 'male' else first_names_female)
            username = f"testuser_{i}"
            
            # Create User
            user, created = User.objects.get_or_create(
                username=username,
                defaults={
                    'email': f"{username}@example.com",
                    'first_name': first_name
                }
            )
            user.set_password('password123') # Easy password for testing
            user.save()

            # Create Profile
            birth_date = date.today() - timedelta(days=random.randint(18*365, 35*365))
            profile, _ = Profile.objects.get_or_create(
                user=user,
                defaults={
                    'display_name': f"{first_name}, {random.randint(18, 35)}",
                    'gender': gender,
                    'birth_date': birth_date,
                    'city': random.choice(cities),
                    'country': 'USA',
                    'bio': random.choice(bios),
                    'is_subscribed': random.choice([True, False]),
                    'is_available': True if gender == 'female' else False
                }
            )

            # Create Preference
            Preference.objects.get_or_create(
                user=user,
                defaults={
                    'age_min': 18,
                    'age_max': 40,
                    'gender_in': 'male,female,other',
                    'distance_km': 50,
                    'city': random.choice(cities)
                }
            )
            created_users.append(user)
            self.stdout.write(self.style.SUCCESS(f'Created: {username} ({gender})'))

        # 4. SEED THE ALGORITHM: Create mock Likes and Matches
        self.stdout.write(self.style.NOTICE('Seeding algorithm data (Likes & Matches)...'))
        
        # Scenario A: Mutual Match (User 1 and User 2 like each other)
        u1, u2 = created_users[0], created_users[1]
        Like.objects.get_or_create(from_user=u1, to_user=u2)
        Like.objects.get_or_create(from_user=u2, to_user=u1)
        Match.objects.get_or_create(user_a=u1, user_b=u2) # Your model's save() will sort the IDs
        self.stdout.write(self.style.SUCCESS(f'✅ MATCH CREATED: {u1.username} & {u2.username}'))

        # Scenario B: One-sided Like (User 3 likes User 4, but User 4 hasn't swiped yet)
        u3, u4 = created_users[2], created_users[3]
        Like.objects.get_or_create(from_user=u3, to_user=u4)
        self.stdout.write(self.style.WARNING(f'⏳ ONE-SIDED LIKE: {u3.username} likes {u4.username}'))

        # Scenario C: User 1 passes on User 5
        u5 = created_users[4]
        Pass.objects.get_or_create(from_user=u1, to_user=u5)
        self.stdout.write(self.style.WARNING(f'❌ PASS RECORDED: {u1.username} passed on {u5.username}'))

        # Scenario D: Random likes to populate the database
        for _ in range(10):
            from_u = random.choice(created_users)
            to_u = random.choice([u for u in created_users if u != from_u])
            Like.objects.get_or_create(from_user=from_u, to_user=to_u)

        self.stdout.write(self.style.SUCCESS('🎉 Database seeding completed successfully!'))
        self.stdout.write(self.style.NOTICE('💡 Test Credentials:'))
        self.stdout.write(self.style.NOTICE('   Username: testuser_1  |  Password: password123'))
        self.stdout.write(self.style.NOTICE('   Username: testuser_2  |  Password: password123'))