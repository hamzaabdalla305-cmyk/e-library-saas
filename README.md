# 📚 المكتبة الإلكترونية (E-Library SaaS)

مشروع Cloud Computing - منصة SaaS لإدارة مكتبة إلكترونية متخصصة في مجالات علوم الحاسوب.

## المميزات المنفذة
- تسجيل دخول وتسجيل حسابات (Authentication)
- قاعدة بيانات (Users, Books, Borrow Records, Subscriptions)
- تصنيفات كتب متخصصة (هندسة البيانات، الذكاء الاصطناعي، الشبكات...)
- صلاحيات مختلفة: أدمن (إضافة/تعديل/حذف) - مستخدم (شراء فقط)
- عملية شراء ودفع وهمية (Mock Payment Gateway)
- خطط اشتراك (Free/Basic/Premium/Enterprise)
- REST API endpoints
- نشر على Render مع PostgreSQL
- تشفير كلمات المرور (Password Hashing)
- HTTPS تلقائي عبر Render
- Logging للعمليات
- CI/CD عبر GitHub Actions
- Unit Testing

## Tech Stack
- Backend: Flask (Python)
- Database: PostgreSQL
- ORM: SQLAlchemy
- Authentication: Flask-Login
- Deployment: Render

## هيكل المشروع
راجع ملف [ARCHITECTURE.md](ARCHITECTURE.md) لمخطط النظام الكامل.

## خطط مستقبلية (Future Scope)
- Multi-tenancy كامل (عزل بيانات كل مؤسسة)
- Payment Gateway حقيقي (Stripe integration)
- Monitoring عبر Grafana/Datadog
- Containerization عبر Docker + Kubernetes

## التشغيل محلياً
