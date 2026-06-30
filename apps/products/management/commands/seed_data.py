"""
Seed data management command.

Usage:
    python manage.py seed_data
"""
import random
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model

from apps.categories.models import Category, CategoryField
from apps.products.models import Product


User = get_user_model()


CATEGORIES_DATA = [
    {
        'name': 'Mobile', 'slug': 'mobile', 'icon': '📱', 'description': 'Smartphones and feature phones',
        'fields': [
            {'name': 'brand', 'label': 'Brand', 'field_type': 'choice', 'choices': ['Apple', 'Samsung', 'OnePlus', 'Xiaomi', 'Realme', 'Vivo', 'Oppo'], 'is_filterable': True, 'is_required': True},
            {'name': 'model', 'label': 'Model', 'field_type': 'text', 'is_required': True},
            {'name': 'ram', 'label': 'RAM', 'field_type': 'number', 'unit': 'GB', 'is_filterable': True},
            {'name': 'storage', 'label': 'Storage', 'field_type': 'number', 'unit': 'GB', 'is_filterable': True},
            {'name': 'processor', 'label': 'Processor', 'field_type': 'text'},
            {'name': 'battery_health', 'label': 'Battery Health', 'field_type': 'number', 'unit': '%'},
            {'name': 'warranty', 'label': 'Under Warranty', 'field_type': 'boolean', 'is_filterable': True},
        ],
    },
    {
        'name': 'Laptop', 'slug': 'laptop', 'icon': '💻', 'description': 'Laptops and notebooks',
        'fields': [
            {'name': 'brand', 'label': 'Brand', 'field_type': 'choice', 'choices': ['Dell', 'HP', 'Lenovo', 'Apple', 'Asus', 'Acer'], 'is_filterable': True, 'is_required': True},
            {'name': 'cpu', 'label': 'CPU', 'field_type': 'text'},
            {'name': 'ram', 'label': 'RAM', 'field_type': 'number', 'unit': 'GB', 'is_filterable': True},
            {'name': 'storage', 'label': 'Storage', 'field_type': 'number', 'unit': 'GB'},
            {'name': 'gpu', 'label': 'GPU', 'field_type': 'text'},
            {'name': 'screen_size', 'label': 'Screen Size', 'field_type': 'number', 'unit': 'inches'},
            {'name': 'warranty', 'label': 'Under Warranty', 'field_type': 'boolean'},
        ],
    },
    {
        'name': 'Tablet', 'slug': 'tablet', 'icon': '📱', 'description': 'Tablets and iPads',
        'fields': [
            {'name': 'brand', 'label': 'Brand', 'field_type': 'choice', 'choices': ['Apple', 'Samsung', 'Lenovo'], 'is_filterable': True, 'is_required': True},
            {'name': 'ram', 'label': 'RAM', 'field_type': 'number', 'unit': 'GB'},
            {'name': 'storage', 'label': 'Storage', 'field_type': 'number', 'unit': 'GB'},
            {'name': 'display_size', 'label': 'Display Size', 'field_type': 'number', 'unit': 'inches'},
        ],
    },
    {
        'name': 'Watch', 'slug': 'watch', 'icon': '⌚', 'description': 'Smartwatches and analog watches',
        'fields': [
            {'name': 'brand', 'label': 'Brand', 'field_type': 'choice', 'choices': ['Apple', 'Samsung', 'Fossil', 'Titan', 'Casio'], 'is_filterable': True, 'is_required': True},
            {'name': 'type', 'label': 'Type', 'field_type': 'choice', 'choices': ['Smartwatch', 'Analog', 'Digital'], 'is_filterable': True},
        ],
    },
    {
        'name': 'Vehicle', 'slug': 'vehicle', 'icon': '🚗', 'description': 'Cars, bikes, scooters',
        'fields': [
            {'name': 'brand', 'label': 'Brand', 'field_type': 'text', 'is_required': True, 'is_filterable': True},
            {'name': 'model', 'label': 'Model', 'field_type': 'text', 'is_required': True},
            {'name': 'year', 'label': 'Year', 'field_type': 'number', 'is_filterable': True},
            {'name': 'km_driven', 'label': 'KM Driven', 'field_type': 'number', 'unit': 'km', 'is_filterable': True},
        ],
    },
    {'name': 'Electronics', 'slug': 'electronics', 'icon': '🔌', 'description': 'TVs, speakers, cameras, gadgets'},
    {'name': 'Furniture', 'slug': 'furniture', 'icon': '🛋️', 'description': 'Sofas, beds, tables, chairs'},
    {'name': 'Books', 'slug': 'books', 'icon': '📚', 'description': 'Textbooks, novels, comics'},
    {'name': 'Toys', 'slug': 'toys', 'icon': '🧸', 'description': 'Toys, games, puzzles'},
    {'name': 'Appliances', 'slug': 'appliances', 'icon': '🏠', 'description': 'Refrigerators, ACs, washing machines'},
]


INDIAN_LOCATIONS = [
    ('TamilNadu', 'Tirupur'), ('TamilNadu', 'Pune'), ('TamilNadu', 'Nagpur'),
    ('Delhi', 'New Delhi'), ('Delhi', 'Dwarka'),
    ('Karnataka', 'Bengaluru'), ('Karnataka', 'Mysuru'),
    ('Tamil Nadu', 'Tirupur'), ('Tamil Nadu', 'Coimbatore'),
    ('Telangana', 'Hyderabad'),
    ('West Bengal', 'Kolkata'),
    ('Gujarat', 'Ahmedabad'), ('Gujarat', 'Surat'),
    ('Rajasthan', 'Jaipur'),
    ('Uttar Pradesh', 'Lucknow'), ('Uttar Pradesh', 'Noida'),
]


SAMPLE_TITLES = {
    'mobile': ['iPhone 13 - 128GB', 'Samsung Galaxy S22', 'OnePlus 11R', 'Xiaomi Redmi Note 12 Pro', 'Realme 10 Pro+'],
    'laptop': ['Dell XPS 13', 'MacBook Air M1', 'HP Pavilion 15', 'Lenovo ThinkPad T490', 'Asus ROG Strix'],
    'tablet': ['iPad Air 4th Gen', 'Samsung Galaxy Tab S8', 'Lenovo Tab P11'],
    'watch': ['Apple Watch Series 7', 'Samsung Galaxy Watch 5', 'Fossil Gen 6', 'Titan Smart Pro'],
    'vehicle': ['Honda Activa 6G', 'Royal Enfield Classic 350', 'Maruti Swift Vxi', 'Bajaj Pulsar 150'],
    'electronics': ['Sony Bravia 43" TV', 'JBL Bluetooth Speaker', 'Canon DSLR Camera', 'Boat Soundbar'],
    'furniture': ['Wooden Sofa Set', 'Queen Size Bed', 'Office Chair', 'Dining Table 6-seater'],
    'books': ['Engineering Textbooks Bundle', 'CAT Prep Books', 'Novels Collection', 'NCERT Class 12 Set'],
    'toys': ['LEGO Technic Set', 'Remote Control Car', 'Board Games Bundle', 'Teddy Bear Large'],
    'appliances': ['Whirlpool Fridge 250L', 'LG AC 1.5 Ton', 'Samsung Washing Machine', 'Philips Microwave'],
}


class Command(BaseCommand):
    help = 'Seed the database with categories, an admin user, and sample listings.'

    def add_arguments(self, parser):
        parser.add_argument('--fresh', action='store_true', help='Delete existing data before seeding')
        parser.add_argument('--listings', type=int, default=20, help='Number of sample listings to create')

    def handle(self, *args, **options):
        if options['fresh']:
            self.stdout.write(self.style.WARNING('Clearing existing data...'))
            Product.objects.all().delete()
            Category.objects.all().delete()
            User.objects.filter(is_staff=False).delete()

        # Admin user
        admin_email = 'admin@Lintro.in'
        if not User.objects.filter(email=admin_email).exists():
            User.objects.create_superuser(
                email=admin_email,
                password='Admin@123!',
                full_name='Admin User',
                mobile_number='+910000000000',
            )
            self.stdout.write(self.style.SUCCESS(f'Admin user created: {admin_email} / Admin@123!'))
        else:
            self.stdout.write(f'Admin already exists: {admin_email}')

        # Categories
        self.stdout.write('Creating categories...')
        for cat_data in CATEGORIES_DATA:
            cat, created = Category.objects.get_or_create(
                slug=cat_data['slug'],
                defaults={
                    'name': cat_data['name'],
                    'icon': cat_data.get('icon', ''),
                    'description': cat_data.get('description', ''),
                },
            )
            if created:
                self.stdout.write(f'  + {cat.name}')
            for field_data in cat_data.get('fields', []):
                CategoryField.objects.get_or_create(
                    category=cat, name=field_data['name'],
                    defaults={
                        'label': field_data['label'],
                        'field_type': field_data['field_type'],
                        'is_required': field_data.get('is_required', False),
                        'is_filterable': field_data.get('is_filterable', False),
                        'choices': field_data.get('choices', []),
                        'unit': field_data.get('unit', ''),
                    },
                )

        # Sample users
        sample_emails = [
            ('ramesh@demo.com', 'Ramesh Kumar', '+919876543210', True),
            ('priya@demo.com', 'Priya Sharma', '+919876543211', True),
            ('arjun@demo.com', 'Arjun Reddy', '+919876543212', True),
            ('sneha@demo.com', 'Sneha Patel', '+919876543213', False),
            ('vikram@demo.com', 'Vikram Singh', '+919876543214', False),
        ]
        sellers = []
        for email, name, mobile, verified in sample_emails:
            user, created = User.objects.get_or_create(
                email=email,
                defaults={
                    'full_name': name,
                    'mobile_number': mobile,
                    'email_verified': True,
                    'is_active': True,
                    'verified_seller': verified,
                    'district': 'Tirupur',
                    'state': 'TamilNadu',
                },
            )
            if created:
                user.set_password('Demo@123!')
                user.save()
                self.stdout.write(f'  + User: {email}')
            sellers.append(user)

        # Sample listings
        self.stdout.write(f'Creating {options["listings"]} sample listings...')
        categories = list(Category.objects.filter(is_active=True))
        conditions = ['new', 'like_new', 'good', 'fair']
        descriptions = [
            'Excellent condition, barely used. Comes with original box and accessories.',
            'Used for 6 months, no scratches. Selling because upgrading.',
            'Perfect working condition. Minor cosmetic wear.',
            'Selling as I am relocating. Pickup from my location preferred.',
            'Bought 1 year ago, under warranty. Bill available.',
        ]

        for i in range(options['listings']):
            cat = random.choice(categories)
            titles = SAMPLE_TITLES.get(cat.slug, ['Sample Item'])
            title = random.choice(titles) + f' #{i+1}'
            state, district = random.choice(INDIAN_LOCATIONS)
            seller = random.choice(sellers)
            price = random.choice([999, 1999, 4999, 9999, 19999, 39999, 59999, 89999, 149999])

            custom_fields = {}
            for cf in cat.custom_fields.all()[:3]:
                if cf.field_type == 'choice' and cf.choices:
                    custom_fields[cf.name] = random.choice(cf.choices)
                elif cf.field_type == 'number':
                    custom_fields[cf.name] = random.choice([4, 8, 16, 32, 64, 128, 256])
                elif cf.field_type == 'boolean':
                    custom_fields[cf.name] = random.choice([True, False])
                else:
                    custom_fields[cf.name] = 'Sample'

            Product.objects.create(
                title=title,
                description=random.choice(descriptions),
                price=price,
                category=cat,
                seller=seller,
                condition=random.choice(conditions),
                location_name=f'{district} area',
                district=district,
                state=state,
                country='India',
                negotiable=random.choice([True, False]),
                custom_fields=custom_fields,
                is_featured=(i < 4),
            )

        self.stdout.write(self.style.SUCCESS(f'Seeded {options["listings"]} listings.'))
        self.stdout.write(self.style.SUCCESS('=' * 60))
        self.stdout.write(self.style.SUCCESS('Seed complete!'))
        self.stdout.write('  Admin login: admin@Lintro.in / Admin@123!')
        self.stdout.write('  Demo users: ramesh@demo.com, priya@demo.com, etc. / Demo@123!')
        self.stdout.write(self.style.SUCCESS('=' * 60))
