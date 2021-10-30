import unittest

from transformation_algebra.type import \
    TypeOperator, TypeSchema, TypeVariable, _, with_parameters, \
    FunctionApplicationError, SubtypeMismatch, \
    ConstraintViolation, ConstrainFreeVariable


class TestType(unittest.TestCase):

    def apply(self, f, x, result=None):
        """
        Test the application of an argument to a function.
        """
        f = f.instance()
        x = x.instance()

        if isinstance(result, type) and issubclass(result, Exception):
            self.assertRaises(result, lambda x: f.apply(x), x)
        elif result:
            actual = f.apply(x)
            expected = result.instance()
            self.assertEqual(actual, expected)
        else:
            f.apply(x)

    def test_parameter_auxiliary(self):
        F, G = TypeOperator(params=2), TypeOperator(params=2)
        A = TypeOperator()
        self.assertEqual(
            with_parameters(F, param=A),
            [F(A, _), F(_, A)]
        )
        self.assertEqual(
            with_parameters(F, G, param=A, at=1),
            [F(A, _), G(A, _)]
        )

    def test_apply_non_function(self):
        A = TypeOperator('A')
        self.apply(A, A, FunctionApplicationError)

    def test_basic_match(self):
        A, B = TypeOperator('A'), TypeOperator('B')
        f = A ** B
        self.apply(f, A, B)

    def test_basic_mismatch(self):
        A, B = TypeOperator('A'), TypeOperator('B')
        f = A ** B
        self.apply(f, B, SubtypeMismatch)

    def test_basic_sub_match(self):
        A = TypeOperator('A')
        B, C = TypeOperator('B', supertype=A), TypeOperator('C', supertype=A)
        f = A ** C
        self.apply(f, B, C)

    def test_basic_sub_mismatch(self):
        A = TypeOperator('A')
        B, C = TypeOperator('B', supertype=A), TypeOperator('C', supertype=A)
        f = B ** C
        self.apply(f, A, SubtypeMismatch)

    def test_compound_match(self):
        F = TypeOperator('F', params=1)
        A, B = TypeOperator('A'), TypeOperator('B')
        f = F(A) ** B
        self.apply(f, F(A), B)

    def test_compound_mismatch(self):
        F = TypeOperator('F', params=1)
        A, B = TypeOperator('A'), TypeOperator('B')
        f = F(A) ** B
        self.apply(f, F(B), SubtypeMismatch)

    def test_compound_sub_match(self):
        A = TypeOperator('A')
        B, C = TypeOperator('B', supertype=A), TypeOperator('C', supertype=A)
        F = TypeOperator('F', params=1)
        f = F(A) ** C
        self.apply(f, F(B), C)

    def test_compound_sub_mismatch(self):
        F = TypeOperator('F', params=1)
        A = TypeOperator('A')
        B, C = TypeOperator('B', supertype=A), TypeOperator('C', supertype=A)
        f = F(B) ** C
        self.apply(f, F(A), SubtypeMismatch)

    def test_variable(self):
        F = TypeOperator('F', params=1)
        A = TypeOperator('A')
        wrap = TypeSchema(lambda α: α ** F(α))
        self.apply(wrap, A, F(A))

    def test_compose(self):
        A, B = TypeOperator('A'), TypeOperator('B')
        compose = TypeSchema(lambda x, y, z: (y ** z) ** (x ** y) ** (x ** z))
        self.apply(compose.apply(A ** B), B ** A, B ** B)

    def test_compose_subtype(self):
        A, B = TypeOperator('A'), TypeOperator('B')
        Asub = TypeOperator('Asub', supertype=A)
        compose = TypeSchema(lambda x, y, z: (y ** z) ** (x ** y) ** (x ** z))
        self.apply(compose.apply(A ** B), B ** Asub, B ** B)

    def test_variable_subtype_mismatch(self):
        A = TypeOperator('A')
        B = TypeOperator('B', supertype=A)
        f = TypeSchema(lambda x: (x ** B) ** x)
        self.apply(f, B ** A, SubtypeMismatch)

    def test_functions_as_arguments1(self):
        A, B = TypeOperator('A'), TypeOperator('B')
        swap = TypeSchema(lambda α, β, γ: (α ** β ** γ) ** (β ** α ** γ))
        f = TypeSchema(lambda x: A ** x ** x)
        self.apply(swap.apply(f).apply(B), A, B)

    def test_functions_as_arguments2(self):
        A = TypeOperator('A')
        B = TypeOperator('B', supertype=A)
        id = TypeSchema(lambda x: x ** x)
        self.apply(id.apply(A ** A), B, A)

    def test_order_of_subtype_application(self):
        # This test is inspired by Traytel et al (2011).
        Basic = TypeOperator('Basic')
        Sub = TypeOperator('Sub', supertype=Basic)
        Other = TypeOperator('Other')
        f = TypeSchema(lambda α: α ** α ** Other)
        self.apply(f.apply(Sub), Basic, Other)
        self.apply(f.apply(Basic), Sub, Other)
        self.apply(f.apply(Basic), Other, SubtypeMismatch)

    def test_order_of_subtype_application_with_constraints(self):
        Super = TypeOperator('Super')
        Basic = TypeOperator('Basic', supertype=Super)
        Sub = TypeOperator('Sub', supertype=Basic)
        Other = TypeOperator('Other')
        f = TypeSchema(lambda α: α ** α ** Other | α @ [Super, Basic])
        self.apply(f.apply(Basic), Sub, Other)
        self.apply(f, Super, ConstraintViolation)

    def test_violation_of_constraints(self):
        F = TypeOperator('F', params=1)
        A = TypeOperator('A')
        B = TypeOperator('B', supertype=A)
        C = TypeOperator('C')
        f = TypeSchema(lambda α: α ** α | α @ [A, F(A)])
        self.apply(f, F(B), F(B))
        self.apply(f, C, ConstraintViolation)

    def test_preservation_of_basic_subtypes_in_constraints(self):
        Super = TypeOperator('Super')
        Basic = TypeOperator('Basic', supertype=Super)
        f = TypeSchema(lambda x: x ** x | x @ [Super])
        self.apply(f, Basic, Basic)

    def test_unification_of_compound_types_in_constraints(self):
        F, G = TypeOperator('F', params=1), TypeOperator('G', params=1)
        A = TypeOperator('A')
        f = TypeSchema(lambda xs, x: xs ** x | xs @ [G(x), F(x)])
        self.apply(f, F(A), A)

    def test_non_unification_of_base_types(self):
        # We can't unify with base types from constraints, as they might be
        # subtypes. So in this case, we know that x is an F, but we don't know
        # that its parameters is exactly A: that might be too general a bound.
        F, A = TypeOperator('F', params=1), TypeOperator('A')
        f = TypeSchema(lambda x: x ** x | x @ F(A))
        result = f.apply(TypeVariable())
        self.assertEqual(result.operator, F)
        self.assertTrue(isinstance(result.params[0], TypeVariable))

    def test_multiple_bounds1(self):
        # This works because B ** B is acceptable for A ** B.
        A = TypeOperator('A')
        B = TypeOperator('B', supertype=A)
        f = TypeSchema(lambda x: (x ** x) ** x)
        self.apply(f, A ** B, B)

    def test_multiple_bounds2(self):
        # This doesn't work because the upper bound B cannot be reconciled
        # with the lower bound A.
        A = TypeOperator('A')
        B = TypeOperator('B', supertype=A)
        f = TypeSchema(lambda x: (x ** x) ** x)
        self.apply(f, B ** A, SubtypeMismatch)

    def test_constrain_wildcard(self):
        A = TypeOperator('A')
        f = TypeSchema(lambda x: x ** x | x @ [_])
        self.apply(f, A, A)

    def test_constrain_free_variable(self):
        f = TypeSchema(lambda x, y, z: x ** x | y @ [x, z])
        g = TypeSchema(lambda x, y, z: x ** x | x @ [y, z])
        self.assertRaises(ConstrainFreeVariable, TypeSchema.instance, f)
        self.assertRaises(ConstrainFreeVariable, TypeSchema.instance, g)

    def test_global_subtype_resolution(self):
        A = TypeOperator('A')
        B = TypeOperator('B', supertype=A)
        f = TypeSchema(lambda x: x ** (x ** x) ** x)
        self.apply(f.apply(B), A ** B, B)
        self.apply(f.apply(A), A ** B, A)

    def test_interdependent_types(self):
        A = TypeOperator('A')
        F, G = TypeOperator('F', 1), TypeOperator('G', 2)
        f = TypeSchema(lambda α, β: α ** β | α @ [F(β), G(_, β)])
        self.apply(f, F(A), A)
        self.apply(f, A, ConstraintViolation)

    def test_subtyping_of_concrete_functions(self):
        Super = TypeOperator('Super')
        Basic = TypeOperator('Basic', supertype=Super)
        Sub = TypeOperator('Sub', supertype=Basic)
        self.assertTrue(Basic ** Basic <= Sub ** Basic)
        self.assertTrue(Basic ** Basic <= Basic ** Super)
        self.assertFalse(Basic ** Basic <= Super ** Basic)
        self.assertFalse(Basic ** Basic <= Basic ** Sub)

    def test_subtyping_of_variables(self):
        x = TypeVariable()
        self.assertEqual(x < x, False)
        self.assertEqual(x <= x, True)

    def test_subtyping_of_variable_functions(self):
        x = TypeVariable()
        Super = TypeOperator('Super')
        Basic = TypeOperator('Basic', supertype=Super)
        Sub = TypeOperator('Sub', supertype=Basic)
        self.assertEqual(x ** Basic <= Sub ** Basic, None)
        self.assertEqual(Basic ** x <= Basic ** Super, None)
        self.assertEqual(Basic ** Basic <= x ** Basic, None)
        self.assertEqual(Basic ** Basic <= Basic ** x, None)

    def test_subtyping_of_wildcard_functions(self):
        Super = TypeOperator('Super')
        Basic = TypeOperator('Basic', supertype=Super)
        Sub = TypeOperator('Sub', supertype=Basic)
        self.assertTrue(_ ** Basic <= Sub ** Basic)
        self.assertTrue(Basic ** _ <= Basic ** Super)
        self.assertTrue(Basic ** Basic <= _ ** Basic)
        self.assertTrue(Basic ** Basic <= Basic ** _)
        self.assertFalse(_ ** Super <= Sub ** Basic)
        self.assertFalse(Sub ** _ <= Basic ** Super)

    def test_constrained_to_base_type(self):
        # See issue #2, which caused an infinite loop
        A = TypeOperator('A')
        f = TypeSchema(lambda x: x ** x | x @ A)
        g = TypeSchema(lambda x, y: (x ** y) ** y)
        self.apply(g, f)

    def test_constrained_to_compound_type(self):
        # See issue #2
        A = TypeOperator('A')
        F = TypeOperator('F', params=1)
        f = TypeSchema(lambda x: x ** x | x @ F(A))
        g = TypeSchema(lambda x, y: (x ** y) ** y)
        self.apply(g, f)

    def test_unification_of_constraint_with_variables(self):
        # See issue #13
        A, B, C = TypeOperator('A'), TypeOperator('B'), TypeOperator('C')
        R2, R3 = TypeOperator('R2', 2), TypeOperator('R3', 3)
        actual = TypeSchema(lambda x:
            R3(A, x, C) | R2(C, B) @ [R2(A, x), R2(C, x)])
        expected = R3(A, B, C)
        self.assertEqual(actual.instance(), expected.instance())

    def test_timely_constraint_check(self):
        # See issue #13
        A, B, F = TypeOperator('A'), TypeOperator('B'), TypeOperator('F', 2)
        f = TypeSchema(lambda r, x: r ** x | r @ [F(A, x), F(B, x)])
        actual = f.apply(F(A, B))
        expected = B
        self.assertEqual(actual.instance(), expected.instance())

    def test_unification_of_constraint_options(self):
        # See issue #11
        A = TypeOperator('A')
        F = TypeOperator('F', params=2)
        actual = TypeSchema(lambda x: x | F(A, A) @ [F(A, x), F(A, x)])
        expected = A
        self.assertEqual(actual.instance(), expected.instance())

    def test_overeager_unification_of_constraint_options(self):
        # See issue #17
        A = TypeOperator('A')
        F = TypeOperator('F', params=2)
        self.assertEqual(F(A, _) <= F(_, A), True)
        x = TypeVariable()
        c = x @ [F(A, _), F(_, A)]
        self.assertEqual(len(c.alternatives), 2)
        c = x @ [F(_, _), F(_, _)]
        self.assertEqual(len(c.alternatives), 1)

    def test_unification_of_constraint_option_subtypes(self):
        # See issue #16
        A = TypeOperator('A')
        B = TypeOperator('B', supertype=A)
        F = TypeOperator('F', params=2)
        f = TypeSchema(lambda x, y: F(x, y) | F(y, A) @ [F(A, x), F(B, x)])
        actual = f.instance().params[0]
        expected = A.instance()
        self.assertEqual(actual, expected)

    def test_constraint_check_on_intertwined_variables1(self):
        # See issue #18
        F = TypeOperator('F', params=2)
        f = TypeSchema(lambda x, y, z: (x ** y) ** z | z @ F(x, y))
        g = TypeSchema(lambda x, y: x ** y)
        x, y = f.apply(g).params
        self.assertEqual(len(x._constraints), 0)
        self.assertEqual(len(y._constraints), 0)

    def test_constraint_check_on_intertwined_variables2(self):
        # See issue #18
        F = TypeOperator('F', params=2)
        f = TypeSchema(lambda x, y: F(x, y) ** y)
        g = TypeSchema(lambda a, b: F(a, b) | F(a, b) @ F(a, b))
        y = f.apply(g)
        self.assertEqual(len(y._constraints), 0)

    def test_reach_all_constraints(self):
        f = TypeSchema(lambda a, b, c: a ** b ** c
            | c @ [b, _] | b @ [c, a] | a @ [b, c]).instance()
        self.assertEqual(len(f[1][1].constraints()), 3)

    def test_reach_all_operators(self):
        A = TypeOperator('A')
        f = TypeSchema(lambda a, b, c: a ** b ** c
            | c @ [b, _] | b @ [a, _] | a @ [A, _]).instance()
        self.assertEqual(f[1][1].operators(), {A})

    def test_curried_function_signature_same_as_uncurried(self):
        # See issue #53
        A, B, C = TypeOperator("A"), TypeOperator("B"), TypeOperator("B")
        self.assertEqual(
            A ** B ** C,
            (A, B) ** C
        )


if __name__ == '__main__':
    unittest.main()
