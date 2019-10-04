import os
import numpy as np
from opencmiss.iron import iron

class Fitting:
    """
    Fitting class
    """

    def __init__(self, instance=1, fitting_type='guass'):
        """
        Create a new instance of a fitting problem.
        """
        self.results_folder = './'

        # Fitting parameters
        self.num_iterations = 1
        self.tau = 0.01
        self.kappa = 0.005
        self.smoothing_parameters = ([
            self.tau,  # tau_1
            self.kappa,  # kappa_11
            self.tau,  # tau_2
            self.kappa,  # kappa_22
            self.kappa,  # kappa_12
            self.tau,  # tau_3
            self.kappa,  # kappa_33
            self.kappa,  # kappa_13
            self.kappa])  # kappa_23
        
        # Set fitting data default
        self.interpolation_type = iron.FieldInterpolationTypes.GAUSS_POINT_BASED
        
        # OpenCMISS user numbers
        self.data_field_user_num = 100 + instance
        self.dependent_field_user_num = 101 + instance
        self.material_field_user_num = 102 + instance
        self.equations_set_field_user_num = 103 + instance
        self.equations_set_user_num = 100 + instance
        self.problem_user_num = 100 + instance
        
        # Instances for setting up fitting problems
        self.data_field = iron.Field()
        self.dependent_field = iron.Field()
        self.material_field = iron.Field()
        self.equations_set_field = iron.Field()
        self.equations_set = iron.EquationsSet()
        self.problem = iron.Problem()

        if fitting_type == 'guass':
            self.specification = (
                [iron.EquationsSetClasses.FITTING,
                 iron.EquationsSetTypes.GAUSS_FITTING_EQUATION,
                 iron.EquationsSetSubtypes.GAUSS_POINT_FITTING,
                 iron.EquationsSetFittingSmoothingTypes.SOBOLEV_VALUE])
            self.data_interpolation_type = \
                iron.FieldInterpolationTypes.GAUSS_POINT_BASED
        elif fitting_type == 'data':
            self.specification = (
                [iron.EquationsSetClasses.FITTING,
                 iron.EquationsSetTypes.DATA_FITTING_EQUATION,
                 iron.EquationsSetSubtypes.DATA_POINT_FITTING,
                 iron.EquationsSetFittingSmoothingTypes.SOBOLEV_VALUE])
            self.data_interpolation_type = \
                iron.FieldInterpolationTypes.DATA_POINT_BASED
        else:
            raise ValueError('Specified fitting type not supported')
        self.problem_specification = ([iron.ProblemClasses.FITTING,
                                       iron.ProblemTypes.DATA_FITTING,
                                       iron.ProblemSubtypes.STATIC_FITTING])

    def set_data_positions(
            self, element_xi=None, element_nums=None, 
            data_point_positions=None, dataset_num=1, data_point_ids=None):
        """
        Sets positions of data as mesh xi or data positions
        """

        # Create data points from given positions
        self.data_point_positions = np.array(data_point_positions)
        self.data_element_nums = element_nums
        self.data_element_xi = element_xi
        self.num_data_points = self.data_point_positions.shape[0]
        num_components = self.data_point_positions.shape[1]
        if data_point_ids is None:
            data_point_ids = np.arange(self.num_data_points)+1
        self.data_point_ids = data_point_ids

        if self.num_data_points != len(self.data_point_ids):
            raise ValueError('Mismatch in data point ids and positions')

        self.data_points = iron.DataPoints()
        self.data_points.CreateStart(
            dataset_num, self.region, self.num_data_points)
        for idx, point_id in enumerate(self.data_point_ids):
            self.data_points.PositionSet(
                int(point_id), self.data_point_positions[idx, :])
        self.data_points.CreateFinish()

        self.data_projection = iron.DataProjection()
        self.data_projection.CreateStart(
            dataset_num, self.data_points, self.geometric_field,
            iron.FieldVariableTypes.U)
        self.data_projection.ProjectionTypeSet(
            iron.DataProjectionProjectionTypes.ALL_ELEMENTS)
        self.data_projection.CreateFinish()

        # Evaluate data projection based on geometric field
        self.data_projection.DataPointsProjectionEvaluate(
            iron.FieldParameterSetTypes.VALUES)
        #
        # if element_xi is not None:
        #     for idx, point_id in enumerate(self.data_point_ids):
        #         xi = self.data_projection.ResultProjectionXiGet(
        #             int(point_id), 3)
        #         self.data_projection.ResultProjectionXiSet(
        #             int(point_id), element_xi[idx, :])
        #         e_num =self.data_projection.ResultElementNumberGet(
        #             int(point_id))
        #         self.data_projection.ResultElementNumberSet(
        #             int(point_id), int(element_nums[idx]))
        #         print('Point            : ', point_id)
        #         print('xi true          : ', element_xi[idx, :])
        #         print('xi projected     : ', xi)
        #         print('element true     : ', int(element_nums[idx]))
        #         print('element projected: ', e_num)
        #
        # else:
        #     raise ValueError('Projection not implemented, element_xi required')

        # Create mesh topology for data projection
        self.mesh.TopologyDataPointsCalculateProjection(self.data_projection)
        # Create decomposition data projection
        self.decomposition.TopologyDataProjectionCalculate()

    def set_data_values(self, values=None, labels=None):
        """
        Sets positions of data as mesh xi or data positions
        """
        self.data_values = np.array(values)
        self.data_labels = labels
        self.num_data_components = self.data_values.shape[1]
        
    def set_results_folder(self, results_folder):
        """
        Sets results folder for exporting solutions
        """
        if not os.path.exists(results_folder):
            os.makedirs(results_folder)
        self.results_folder = results_folder

    def set_smoothing_parameters(self, smoothing_parameters):
        """
        Sets all smoothing parameters.
        """
        if len(smoothing_parameters) == 9:
            self.smoothing_parameters = smoothing_parameters
            self.update_material_field()
        else:
            raise ValueError('9 smoothing parameters required')

    def set_tau(self, tau):
        """
        Sets tau fitting parameters for all required field components.
        """
        self.tau = tau
        self.smoothing_parameters = ([
            self.tau,  # tau_1
            self.kappa,  # kappa_11
            self.tau,  # tau_2
            self.kappa,  # kappa_22
            self.kappa,  # kappa_12
            self.tau,  # tau_3
            self.kappa,  # kappa_33
            self.kappa,  # kappa_13
            self.kappa])  # kappa_23
        self.update_material_field()

    def set_kappa(self, kappa):
        """
        Sets kappa fitting parameters for all required field components.
        """
        self.kappa = kappa
        self.smoothing_parameters = ([
            self.tau,  # tau_1
            self.kappa,  # kappa_11
            self.tau,  # tau_2
            self.kappa,  # kappa_22
            self.kappa,  # kappa_12
            self.tau,  # tau_3
            self.kappa,  # kappa_33
            self.kappa,  # kappa_13
            self.kappa])  # kappa_23
        self.update_material_field()
        
    def set_region(self, region):
        """
        Sets region for fitting.
        """
        self.region = region

    def set_mesh(self, mesh):
        """
        Sets mesh for fitting.
        """
        self.mesh = mesh
        
    def set_decomposition(self, decomposition):
        """
        Sets decomposition for fitting.
        """
        self.decomposition = decomposition
        
    def set_geometric_field(self, geometric_field):
        """
        Sets geometric field for fitting.
        """
        self.geometric_field = geometric_field

    def setup_fields(
            self, scaling_type=iron.FieldScalingTypes.NONE):
        """
        Sets up the field for a fitting problem.
        """
        components = range(1, self.num_data_components + 1)
        mesh_component = 1

        # Setup data field
        variable_types = [iron.FieldVariableTypes.U, iron.FieldVariableTypes.V]
        variable_labels = ['data', 'weight']
        num_variables = len(variable_types)
        self.data_field.CreateStart(self.data_field_user_num, self.region)
        self.data_field.TypeSet(iron.FieldTypes.GENERAL)
        self.data_field.MeshDecompositionSet(self.decomposition)
        self.data_field.GeometricFieldSet(self.geometric_field)
        self.data_field.DependentTypeSet(iron.FieldDependentTypes.INDEPENDENT)
        self.data_field.NumberOfVariablesSet(num_variables)
        self.data_field.VariableTypesSet(variable_types)
        for idx, variable_type in enumerate(variable_types):
            self.data_field.VariableLabelSet(variable_type,
                                             variable_labels[idx])
            self.data_field.NumberOfComponentsSet(
                variable_type, self.num_data_components)
            for component_idx, component in enumerate(components):
                self.data_field.ComponentMeshComponentSet(
                    variable_type, component, mesh_component)
                self.data_field.ComponentInterpolationSet(
                    variable_type, component, self.data_interpolation_type)
                if variable_type == iron.FieldVariableTypes.U:
                    self.data_field.ComponentLabelSet(
                        variable_type, component, self.data_labels[component_idx])
        self.data_field.ScalingTypeSet(scaling_type)
        self.data_field.DataProjectionSet(self.data_projection)
        self.data_field.CreateFinish()

        # Initialise Gauss point weight field to 1.0
        variable_type = iron.FieldVariableTypes.V
        for component in components:
            self.data_field.ComponentValuesInitialiseDP(
                variable_type, iron.FieldParameterSetTypes.VALUES, component,
                1.0)

        # Setup fitting solution field
        variable_types = ([iron.FieldVariableTypes.U,
                           iron.FieldVariableTypes.DELUDELN])
        num_variables = len(variable_types)
        
        self.dependent_field.CreateStart(
            self.dependent_field_user_num, self.region)
        self.dependent_field.TypeSet(iron.FieldTypes.GENERAL)
        self.dependent_field.DependentTypeSet(
            iron.FieldDependentTypes.DEPENDENT)
        self.dependent_field.MeshDecompositionSet(self.decomposition)
        self.dependent_field.GeometricFieldSet(self.geometric_field)
        self.dependent_field.VariableLabelSet(
            iron.FieldVariableTypes.U, "fitted_field")
        self.dependent_field.NumberOfVariablesSet(num_variables)
        for variable_type in variable_types:
            self.dependent_field.NumberOfComponentsSet(
                variable_type, self.num_data_components)
            for component_idx, component in enumerate(components):
                self.dependent_field.ComponentMeshComponentSet(
                    variable_type, component, mesh_component)
                if variable_type == iron.FieldVariableTypes.U:
                    self.dependent_field.ComponentLabelSet(
                        variable_type, component,
                        self.data_labels[component_idx])
        self.dependent_field.ScalingTypeSet(scaling_type)
        self.dependent_field.CreateFinish()

        # Set Sobolev smoothing parameters - kappa and tau
        self.num_smoothing_components = 9
        self.smoothing_components = range(1, self.num_smoothing_components + 1)
        self.material_field.CreateStart(
            self.material_field_user_num, self.region)
        self.material_field.TypeSet(iron.FieldTypes.MATERIAL)
        self.material_field.MeshDecompositionSet(self.decomposition)
        self.material_field.GeometricFieldSet(self.geometric_field)
        self.material_field.NumberOfComponentsSet(
            iron.FieldVariableTypes.U, self.num_smoothing_components)
        self.material_field.VariableLabelSet(
            iron.FieldVariableTypes.U, 'SmoothingParameters')
        self.material_field.ScalingTypeSet(scaling_type)
        self.material_field.CreateFinish()

        # Set smoothing parameters
        self.update_material_field()

        # Set data field
        self.update_data_field()
        
    def update_material_field(self):
        """
        Updates the material field with a set of smoothing parameters.
        """
        for component_idx, component in enumerate(self.smoothing_components):
            self.material_field.ComponentValuesInitialiseDP(
                iron.FieldVariableTypes.U, iron.FieldParameterSetTypes.VALUES,
                component, self.smoothing_parameters[component_idx])

    def update_data_field(self):
        """
        Updates the data field.
        """

        if self.data_interpolation_type != \
                iron.FieldInterpolationTypes.DATA_POINT_BASED:
            raise ValueError('Only setting data point based fields supported')

        for idx, point_id in enumerate(self.data_point_ids):
            element_num = self.data_projection.ResultElementNumberGet(
                int(point_id))
            for component_idx, component in enumerate(
                    np.arange(self.num_data_components)+1):
                self.data_field.ParameterSetUpdateElementDataPointDP(
                    iron.FieldVariableTypes.U, 
                    iron.FieldParameterSetTypes.VALUES,
                    element_num, int(point_id),
                    int(component), self.data_values[idx, component_idx])

    def setup_equations(self):
        """
        Setup the fitting equations.
        """
        self.equations_set.CreateStart(self.equations_set_user_num,
                                       self.region, self.geometric_field,
                                       self.specification,
                                       self.equations_set_field_user_num,
                                       self.equations_set_field)
        self.equations_set.CreateFinish()

        self.equations_set.DependentCreateStart(self.dependent_field_user_num,
                                                self.dependent_field)
        self.equations_set.DependentCreateFinish()

        self.equations_set.IndependentCreateStart(self.data_field_user_num,
                                                  self.data_field)
        self.equations_set.IndependentCreateFinish()

        self.equations_set.MaterialsCreateStart(self.material_field_user_num,
                                                self.material_field)
        self.equations_set.MaterialsCreateFinish()

        #self.equations_set.DerivedCreateStart(
        #    self.data_field_user_num, self.data_field)
        #self.equations_set.DerivedVariableSet(
        #    iron.EquationsSetDerivedTensorTypes.CAUCHY_STRESS,
        #    iron.FieldVariableTypes.U)
        #self.equations_set.DerivedCreateFinish()

        self.equations = iron.Equations()
        self.equations_set.EquationsCreateStart(self.equations)
        self.equations.SparsityTypeSet(iron.EquationsSparsityTypes.SPARSE)
        self.equations.OutputTypeSet(iron.EquationsOutputTypes.NONE)
        self.equations_set.EquationsCreateFinish()

    def setup_problem(self):
        """
        Setup the fitting problem.
        """
        # Create fitting problem
        self.problem.CreateStart(
            self.problem_user_num, self.problem_specification)
        self.problem.CreateFinish()

        self.problem.ControlLoopCreateStart()
        self.problem.ControlLoopCreateFinish()

        self.solver = iron.Solver()
        self.problem.SolversCreateStart()
        self.problem.SolverGet(
            [iron.ControlLoopIdentifiers.NODE], 1, self.solver)
        # self.solver.OutputTypeSet(iron.SolverOutputTypes.NONE)
        self.solver.OutputTypeSet(iron.SolverOutputTypes.PROGRESS)
        # self.solver.LinearTypeSet(iron.LinearSolverTypes.DIRECT)
        # self.solver.LibraryTypeSet(iron.SolverLibraries.UMFPACK) # UMFPACK/SUPERLU
        self.solver.LinearTypeSet(iron.LinearSolverTypes.ITERATIVE)
        self.solver.LinearIterativeMaximumIterationsSet(5000)
        self.solver.LinearIterativeAbsoluteToleranceSet(1.0E-10)
        self.solver.LinearIterativeRelativeToleranceSet(1.0E-05)
        self.problem.SolversCreateFinish()

        self.solver = iron.Solver()
        self.solver_equations = iron.SolverEquations()
        self.problem.SolverEquationsCreateStart()
        self.problem.SolverGet(
            [iron.ControlLoopIdentifiers.NODE], 1, self.solver)
        self.solver.SolverEquationsGet(self.solver_equations)
        self.solver_equations.SparsityTypeSet(
            iron.SolverEquationsSparsityTypes.SPARSE)
        equationsSetIndex = self.solver_equations.EquationsSetAdd(
            self.equations_set)
        self.problem.SolverEquationsCreateFinish()

        self.boundary_conditions = iron.BoundaryConditions()
        self.solver_equations.BoundaryConditionsCreateStart(
            self.boundary_conditions)
        self.solver_equations.BoundaryConditionsCreateFinish()

    def solve(self):
        """
        Peform fitting.
        """
        # Solve the problem
        for iteration_num in range(1, self.num_iterations + 1):
            self.problem.Solve()
            self.export(iteration_num)

    def finalise(self):
        """
        Finalise the fitting problem.
        """
        self.problem.Finalise()

    def export(self, iteration_num):
        """
        Export the fitting solutions for the selected iteration number.
        """
        self.set_results_folder(self.results_folder)
        export_path = os.path.join(
            self.results_folder,
            "fitting_results_iteration_" + str(iteration_num))
    
        fields = iron.Fields()
        fields.AddField(self.geometric_field)
        fields.AddField(self.dependent_field)
        fields.NodesExport(export_path, "FORTRAN")
        fields.ElementsExport(export_path, "FORTRAN")
        fields.Finalise()
